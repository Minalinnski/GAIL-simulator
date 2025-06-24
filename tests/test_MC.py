# tests/test_monte_carlo_rtp.py
import sys
import os
import time
import logging
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
from typing import Dict, List, Tuple, Any

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging
logging.basicConfig(level=logging.WARNING)

from src.infrastructure.config.loaders.yaml_loader import YamlConfigLoader
from src.infrastructure.config.validators.schema_validator import SchemaValidator
from src.infrastructure.rng.rng_provider import RNGProvider

from src.domain.machine.factories.machine_factory import MachineFactory
from src.domain.machine.entities.slot_machine import SlotMachine


def run_monte_carlo_rtp_test(
    machine_id: str, 
    machine_config_path: str, 
    num_spins: int = 1000000, 
    bet_amount: float = 1.0,
    batch_size: int = 10000,
    show_progress: bool = True
) -> Dict[str, Any]:
    """
    运行蒙特卡洛RTP测试，模拟大量旋转并分析结果。
    
    Args:
        machine_id: 老虎机ID
        machine_config_path: 老虎机配置文件路径
        num_spins: 总旋转次数
        bet_amount: 每次旋转的投注金额
        batch_size: 每批次旋转数量
        show_progress: 是否显示进度条
        
    Returns:
        测试结果统计信息
    """
    print(f"Starting Monte Carlo RTP test for {machine_id}")
    print(f"Configuration: {machine_config_path}")
    print(f"Simulating {num_spins:,} spins with bet amount {bet_amount}")
    
    # 创建配置加载器和验证器
    validator = SchemaValidator()
    config_loader = YamlConfigLoader(validator)
    
    # 创建RNG提供器
    rng_provider = RNGProvider()
    
    # 创建机器工厂
    machine_factory = MachineFactory(rng_provider)
    
    # 加载配置
    try:
        machine_config = config_loader.load_file(machine_config_path)
    except Exception as e:
        print(f"Error loading machine configuration: {str(e)}")
        return {}
    
    # 创建老虎机
    machine = machine_factory.create_machine(machine_id, machine_config)

    #print(machine.get_info())
    
    # 运行测试
    start_time = time.time()
    
    # 统计数据
    total_bet = 0.0
    total_win = 0.0
    base_game_win = 0.0  # 基础游戏赢额
    free_spins_win = 0.0  # 免费旋转赢额
    wins_count = 0
    free_spins_count = 0
    free_spins_total = 0  # 所有触发的免费旋转次数
    big_wins_count = 0  # 大于10倍投注的奖励
    spin_results = []
    running_rtps = []
    
    # 每批次旋转
    num_batches = (num_spins + batch_size - 1) // batch_size
    
    # 创建进度条
    pbar = tqdm(total=num_spins) if show_progress else None
    
    for batch in range(num_batches):
        current_batch_size = min(batch_size, num_spins - batch * batch_size)
        
        # 批量旋转
        for _ in range(current_batch_size):
            # 执行旋转
            grid, trigger_free, free_remaining = machine.spin()
            
            # 评估基础游戏赢额
            win_data = machine.evaluate_win(
                grid=grid,
                bet=bet_amount,
                in_free=False,
                active_lines=None  # 使用所有赢线
            )
            
            win_amount = win_data.get("total_win", 0.0)
            
            # 更新基础游戏统计
            total_bet += bet_amount  # 基础游戏投注计入总投注
            total_win += win_amount
            base_game_win += win_amount  # 记录基础游戏赢额
            
            if win_amount > 0:
                wins_count += 1
                
            if win_amount >= bet_amount * 10:
                big_wins_count += 1
                
            # 如果触发免费旋转，执行免费旋转序列
            if trigger_free:
                free_spins_count += 1  # 增加免费旋转触发次数
                free_spins_total += free_remaining  # 增加总免费旋转次数
                
                # 免费旋转使用相同的投注额但不计入总投注
                current_free_spin_win = 0.0
                
                # 处理免费旋转序列
                in_free_spins = True
                remaining_free_spins = free_remaining
                
                while in_free_spins and remaining_free_spins > 0:
                    # 执行免费旋转
                    free_grid, retrigger, new_remaining = machine.spin(
                        in_free=True,
                        num_free_left=remaining_free_spins
                    )
                    
                    # 评估免费旋转赢额，使用免费旋转乘数
                    free_win_data = machine.evaluate_win(
                        grid=free_grid,
                        bet=bet_amount,  # 使用触发时的投注额
                        in_free=True,
                        active_lines=None
                    )
                    
                    free_win_amount = free_win_data.get("total_win", 0.0)
                    
                    # 更新统计
                    total_win += free_win_amount  # 免费旋转赢额计入总赢额
                    free_spins_win += free_win_amount  # 记录免费旋转赢额
                    current_free_spin_win += free_win_amount
                    
                    # 更新剩余免费旋转次数
                    if retrigger:
                        # 如果重新触发，增加免费旋转次数但不计为新的触发
                        free_spins_total += new_remaining - remaining_free_spins
                    
                    remaining_free_spins = new_remaining
                    
                    # 检查免费旋转是否结束
                    if remaining_free_spins <= 0:
                        in_free_spins = False
            
            # 保存当前RTP
            current_rtp = total_win / total_bet if total_bet > 0 else 0
            running_rtps.append(current_rtp)
            
            # 保存结果
            if len(spin_results) < 1000:  # 只保存前1000个旋转，用于分析
                spin_results.append({
                    "grid": grid,
                    "bet": bet_amount,
                    "base_win": win_amount,
                    "triggered_free": trigger_free,
                    "free_spins_win": current_free_spin_win if trigger_free else 0.0,
                    "total_win": win_amount + (current_free_spin_win if trigger_free else 0.0)
                })
        
        # 更新进度条
        if pbar:
            pbar.update(current_batch_size)
    
    # 关闭进度条
    if pbar:
        pbar.close()
    
    end_time = time.time()
    duration = end_time - start_time
    
    # 计算最终统计
    final_rtp = total_win / total_bet if total_bet > 0 else 0
    base_game_rtp = base_game_win / total_bet if total_bet > 0 else 0
    free_spins_rtp = free_spins_win / total_bet if total_bet > 0 else 0
    
    win_rate = wins_count / num_spins
    free_spins_rate = free_spins_count / num_spins
    avg_free_spins = free_spins_total / free_spins_count if free_spins_count > 0 else 0
    big_win_rate = big_wins_count / num_spins
    
    # 绘制RTP收敛图
    plt.figure(figsize=(12, 6))
    
    # 只绘制一部分点以提高性能
    sample_indices = np.linspace(0, len(running_rtps) - 1, min(10000, len(running_rtps))).astype(int)
    plt.plot(sample_indices, [running_rtps[i] for i in sample_indices])
    
    plt.axhline(y=final_rtp, color='r', linestyle='-', label=f'Final RTP: {final_rtp:.4f}')
    plt.axhline(y=base_game_rtp, color='g', linestyle='--', label=f'Base Game RTP: {base_game_rtp:.4f}')
    plt.axhline(y=free_spins_rtp, color='b', linestyle='--', label=f'Free Spins RTP: {free_spins_rtp:.4f}')
    
    plt.xlabel('Spins')
    plt.ylabel('RTP')
    plt.title(f'RTP Convergence for {machine_id}')
    plt.grid(True)
    plt.legend()
    
    # 保存图表
    os.makedirs("tests/outputs", exist_ok=True)
    plt.savefig(f"tests/outputs/{machine_id}_rtp_convergence.png")
    
    # 打印结果
    print("\nTest Results:")
    print(f"Total spins: {num_spins:,}")
    print(f"Total bet: {total_bet:,.2f}")
    print(f"Total win: {total_win:,.2f}")
    print(f"  Base game win: {base_game_win:,.2f}")
    print(f"  Free spins win: {free_spins_win:,.2f}")
    print(f"Final RTP: {final_rtp:.6f} ({final_rtp*100:.4f}%)")
    print(f"  Base game RTP: {base_game_rtp:.6f} ({base_game_rtp*100:.4f}%)")
    print(f"  Free spins RTP: {free_spins_rtp:.6f} ({free_spins_rtp*100:.4f}%)")
    print(f"Win rate: {win_rate:.4f} ({win_rate*100:.2f}%)")
    print(f"Free spins trigger rate: {free_spins_rate:.6f} ({free_spins_rate*100:.4f}%)")
    print(f"Average free spins per trigger: {avg_free_spins:.2f}")
    print(f"Big win rate: {big_win_rate:.6f} ({big_win_rate*100:.4f}%)")
    print(f"Test completed in {duration:.2f} seconds ({num_spins/duration:.2f} spins/second)")
    
    # 绘制收益分布饼图
    plt.figure(figsize=(8, 8))
    labels = ['Base Game', 'Free Spins']
    sizes = [base_game_win, free_spins_win]
    explode = (0, 0.1)  # 让免费旋转部分突出显示
    
    plt.pie(sizes, explode=explode, labels=labels, autopct='%1.1f%%',
            shadow=True, startangle=90,
            colors=['lightgreen', 'lightblue'])
    plt.axis('equal')  # 保持圆形
    plt.title(f'Win Distribution for {machine_id}')
    plt.savefig(f"tests/outputs/{machine_id}_win_distribution.png")
    
    # 返回结果
    return {
        "machine_id": machine_id,
        "total_spins": num_spins,
        "total_bet": total_bet,
        "total_win": total_win,
        "base_game_win": base_game_win,
        "free_spins_win": free_spins_win,
        "rtp": final_rtp,
        "base_game_rtp": base_game_rtp,
        "free_spins_rtp": free_spins_rtp,
        "win_rate": win_rate,
        "free_spins_rate": free_spins_rate,
        "free_spins_total": free_spins_total,
        "avg_free_spins_per_trigger": avg_free_spins,
        "big_win_rate": big_win_rate,
        "duration": duration,
        "spins_per_second": num_spins/duration,
        "running_rtps": running_rtps[::1000],  # 每1000个点采样一次
        "spin_results": spin_results[:100]  # 只保留前100个结果
    }


def compare_machines_rtp(machine_configs: List[Tuple[str, str]], num_spins_per_machine: int = 100000):
    """
    比较多个老虎机的RTP。
    
    Args:
        machine_configs: 老虎机配置列表，每个元素为 (machine_id, config_path)
        num_spins_per_machine: 每个老虎机的旋转次数
    """
    results = []
    
    for machine_id, config_path in machine_configs:
        result = run_monte_carlo_rtp_test(
            machine_id=machine_id,
            machine_config_path=config_path,
            num_spins=num_spins_per_machine,
            show_progress=True
        )
        results.append(result)
    
    # 比较结果
    print("\nMachines Comparison:")
    print(f"{'Machine ID':<15} {'Total RTP':<10} {'Base RTP':<10} {'Free RTP':<10} {'Free Trig':<10}")
    print("-" * 65)
    
    for result in results:
        print(f"{result['machine_id']:<15} " +
              f"{result['rtp']*100:>9.4f}% " +
              f"{result['base_game_rtp']*100:>9.4f}% " +
              f"{result['free_spins_rtp']*100:>9.4f}% " +
              f"{result['free_spins_rate']*100:>9.4f}%")

    # 绘制比较图 - 分解RTP
    plt.figure(figsize=(12, 8))
    x = np.arange(len(results))
    width = 0.35
    
    base_rtps = [r['base_game_rtp'] for r in results]
    free_rtps = [r['free_spins_rtp'] for r in results]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    rects1 = ax.bar(x - width/2, [r*100 for r in base_rtps], width, label='Base Game RTP')
    rects2 = ax.bar(x + width/2, [r*100 for r in free_rtps], width, label='Free Spins RTP')
    
    # 添加总RTP点
    ax.scatter(x, [r['rtp']*100 for r in results], color='red', s=50, label='Total RTP')
    
    ax.set_ylabel('RTP (%)')
    ax.set_title('RTP Breakdown Comparison')
    ax.set_xticks(x)
    ax.set_xticklabels([r['machine_id'] for r in results])
    ax.legend()
    
    # 在每个柱上添加数值标签
    def autolabel(rects):
        for rect in rects:
            height = rect.get_height()
            ax.annotate(f'{height:.2f}%',
                        xy=(rect.get_x() + rect.get_width()/2, height),
                        xytext=(0, 3),  # 3点垂直偏移
                        textcoords="offset points",
                        ha='center', va='bottom')
    
    autolabel(rects1)
    autolabel(rects2)
    
    fig.tight_layout()
    
    # 保存图表
    os.makedirs("tests/outputs", exist_ok=True)
    plt.savefig("tests/outputs/machines_rtp_breakdown.png")


if __name__ == "__main__":
    # 单机测试
    results = run_monte_carlo_rtp_test(
        machine_id="default",
        machine_config_path="src/application/config/machines/default_machine.yaml",
        num_spins=10_000_000,
        bet_amount=1.0
    )
    
    # 多机测试
    """
    compare_machines_rtp([
        ("default", "src/application/config/machines/default_machine.yaml"),
        ("high_variance", "src/application/config/machines/high_variance.yaml"),
        ("low_variance", "src/application/config/machines/low_variance.yaml")
    ], num_spins_per_machine=50000)
    """