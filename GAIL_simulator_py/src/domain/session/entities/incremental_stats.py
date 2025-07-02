# src/domain/session/entities/incremental_stats.py
from dataclasses import dataclass
import math
from typing import Dict, List, Any, Optional, Tuple

@dataclass
class IncrementalStats:
    """
    用于增量计算统计量的类，基于扩展的Welford算法。
    允许在不保留完整数据的情况下计算准确的均值、方差、偏度和峰度。
    """
    count: int = 0
    mean: float = 0.0
    
    # 中心矩 (central moments)
    M2: float = 0.0  # 用于计算m_2 (二阶中心矩)
    M3: float = 0.0  # 用于计算m_3 (三阶中心矩)
    M4: float = 0.0  # 用于计算m_4 (四阶中心矩)
    
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    sum_values: float = 0.0  # 保留总和，用于简单计算和查询
    
    def update(self, new_value: float) -> None:
        """更新统计量，使用扩展的Welford算法"""
        # 更新最小值和最大值
        if self.min_value is None or new_value < self.min_value:
            self.min_value = new_value
        if self.max_value is None or new_value > self.max_value:
            self.max_value = new_value
            
        # 更新总和
        self.sum_values += new_value
        
        # 更新计数
        n1 = self.count  # 旧计数
        self.count += 1  # 新计数
        
        if self.count == 1:
            # 第一个值直接设置均值
            self.mean = new_value
            return
        
        # 计算增量
        delta = new_value - self.mean
        delta_n = delta / self.count
        term1 = delta * delta_n * n1
        
        # 更新四阶矩 (用于峰度)
        self.M4 += term1 * delta_n * delta_n * (self.count*self.count - 3*self.count + 3) + 6 * delta_n * delta_n * self.M2 - 4 * delta_n * self.M3
        
        # 更新三阶矩 (用于偏度)
        self.M3 += term1 * delta_n * (self.count - 2) - 3 * delta_n * self.M2
        
        # 更新二阶矩 (用于方差)
        self.M2 += term1
        
        # 更新均值
        self.mean += delta_n
    
    def _get_central_moment(self, k: int) -> float:
        """
        获取第k阶中心矩 m_k。
        根据定义: m_k = (1/n) * sum((x_i - mean)^k)
        """
        if self.count == 0:
            return 0.0
            
        if k == 1:
            return 0.0  # 一阶中心矩总是0
        elif k == 2:
            return self.M2 / self.count  # m_2
        elif k == 3:
            return self.M3 / self.count  # m_3
        elif k == 4:
            return self.M4 / self.count  # m_4
        else:
            raise ValueError(f"不支持的中心矩阶数: {k}")
    
    def get_variance(self, population: bool = False) -> float:
        """
        获取方差
        population=True: 总体方差 (除以n)
        population=False: 样本方差 (除以n-1)
        
        根据公式: s^2 = [K/(K-1)] * m_2
        """
        if self.count < 2:
            return 0.0
            
        m2 = self._get_central_moment(2)
        
        if population:
            return m2  # 总体方差就是m_2
        else:
            # 样本方差需要乘以校正因子 K/(K-1)
            return m2 * (self.count / (self.count - 1))
    
    def get_std_dev(self, population: bool = False) -> float:
        """获取标准差"""
        return math.sqrt(self.get_variance(population))
    
    def get_skewness(self) -> float:
        """
        获取偏度 (Fisher-Pearson系数)
        
        根据公式: g_1 = [K^2/((K-1)(K-2))] * [m_3/s^3]
        或等价地: g_1 = [K^2/((K-1)(K-2))] * [m_3/m_2^(3/2)]
        """
        if self.count < 3:
            return 0.0
            
        m2 = self._get_central_moment(2)
        m3 = self._get_central_moment(3)
        
        if m2 == 0:
            return 0.0
        
        # 计算使用精确公式
        # g_1 = [K^2/((K-1)(K-2))] * [m_3/m_2^(3/2)]
        correction = (self.count**2) / ((self.count-1) * (self.count-2))
        return correction * (m3 / (m2 ** 1.5))
    
    def get_kurtosis(self) -> float:
        """
        获取无偏峰度 (Unbiased Kurtosis)
        
        使用公式:
        gamma_2 = [K^2((K+1)m_4 - 3(K-1)m_2^2)]/[(K-1)(K-2)(K-3)] * [(K-1)^2/(K^2 m_2^2)]
        """
        if self.count < 4:
            return 0.0
            
        m2 = self._get_central_moment(2)
        m4 = self._get_central_moment(4)
        
        if m2 == 0:
            return 0.0
            
        n = self.count
        
        # 计算使用精确公式
        term1 = (n**2) * ((n+1)*m4 - 3*(n-1)*(m2**2))
        term2 = (n-1) * (n-2) * (n-3)
        term3 = ((n-1)**2) / (n**2 * m2**2)
        
        return (term1 / term2) * term3
    
    def get_excess_kurtosis(self) -> float:
        """
        获取偏峰度 (Biased Excess Kurtosis)
        
        使用公式: g_2 = m_4/m_2^2 - 3
        """
        if self.count < 4:
            return 0.0
            
        m2 = self._get_central_moment(2)
        m4 = self._get_central_moment(4)
        
        if m2 == 0:
            return 0.0
            
        # 计算使用精确公式
        return (m4 / (m2**2)) - 3
        
    def merge(self, other: 'IncrementalStats') -> 'IncrementalStats':
        """
        合并两个增量统计对象
        """
        if other.count == 0:
            return self
        if self.count == 0:
            return other
            
        result = IncrementalStats()
        
        # 合并计数
        result.count = self.count + other.count
        
        # 合并最小最大值
        result.min_value = min(self.min_value, other.min_value) if self.min_value is not None and other.min_value is not None else (self.min_value or other.min_value)
        result.max_value = max(self.max_value, other.max_value) if self.max_value is not None and other.max_value is not None else (self.max_value or other.max_value)
        
        # 合并总和
        result.sum_values = self.sum_values + other.sum_values
        
        # 合并均值 (加权平均)
        result.mean = (self.mean * self.count + other.mean * other.count) / result.count
        
        # 计算均值差异
        delta = other.mean - self.mean
        
        # 合并二阶矩 (M2)
        result.M2 = self.M2 + other.M2 + (delta**2) * self.count * other.count / result.count
        
        # 合并三阶矩 (M3)
        n1 = self.count
        n2 = other.count
        n = n1 + n2
        
        delta_cubed = delta**3
        result.M3 = self.M3 + other.M3
        result.M3 += delta_cubed * n1 * n2 * (n1 - n2) / (n * n)
        result.M3 += 3 * delta * (n1 * other.M2 - n2 * self.M2) / n
        
        # 合并四阶矩 (M4)
        delta_squared = delta * delta
        delta_quad = delta_squared * delta_squared
        
        result.M4 = self.M4 + other.M4
        result.M4 += delta_quad * n1 * n2 * (n1*n1 - n1*n2 + n2*n2) / (n*n*n)
        result.M4 += 6 * delta_squared * (n1*n1 * other.M2 + n2*n2 * self.M2) / (n*n)
        result.M4 += 4 * delta * (n1 * other.M3 - n2 * self.M3) / n
        
        return result
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        # 计算中心矩
        m2 = self._get_central_moment(2)
        m3 = self._get_central_moment(3)
        m4 = self._get_central_moment(4)
        
        # 样本方差
        sample_variance = self.get_variance(population=False)
        
        return {
            "count": self.count,
            "mean": self.mean,
            "variance": sample_variance,
            "std_dev": math.sqrt(sample_variance) if sample_variance > 0 else 0.0,
            "skewness": self.get_skewness(),
            "kurtosis": self.get_kurtosis(),
            "excess_kurtosis": self.get_excess_kurtosis(),
            "min": self.min_value,
            "max": self.max_value,
            "sum": self.sum_values,
            # 为了诊断和调试，也包含原始矩
            "m2": m2,
            "m3": m3,
            "m4": m4
        }