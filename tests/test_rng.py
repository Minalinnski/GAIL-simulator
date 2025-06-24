# tests/test_rng_distribution.py
import unittest
import sys
import os
import time
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Any, Tuple

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.infrastructure.rng.strategies.mersenne_rng import MersenneTwisterRNG
from src.infrastructure.rng.strategies.numpy_rng import NumpyRNG


class TestRNGDistribution(unittest.TestCase):
    """Test RNG distributions with large sample sizes."""

    def setUp(self):
        """Set up RNG instances."""
        self.mersenne_rng = MersenneTwisterRNG(seed_value=12345)
        self.numpy_rng = NumpyRNG(seed_value=12345)
        
        # Default parameters
        self.min_val = 0
        self.max_val = 999
        
        # Number of bins for histogram
        self.num_bins = 100
        
        # Directory for saving plots
        self.output_dir = os.path.join(os.path.dirname(__file__), 'outputs')
        os.makedirs(self.output_dir, exist_ok=True)
        
    def test_mersenne_distribution_int(self):
        """Test distribution of 100M integer samples with Mersenne Twister."""
        print("\nTesting Mersenne Twister distribution (100M samples)...")
        
        # Number of samples
        n_samples = 100_000_000
        batch_size = 1_000_000
        
        # Create bins
        bins = np.linspace(self.min_val, self.max_val + 1, self.num_bins + 1)
        counts = np.zeros(self.num_bins)
        
        # Generate samples in batches and bin them
        start_time = time.time()
        for i in range(0, n_samples, batch_size):
            batch = self.mersenne_rng.get_batch_ints(self.min_val, self.max_val, batch_size)
            batch_counts, _ = np.histogram(batch, bins=bins)
            counts += batch_counts
            
            # Print progress
            if (i + batch_size) % 10_000_000 == 0:
                progress = (i + batch_size) / n_samples * 100
                elapsed = time.time() - start_time
                print(f"  Progress: {progress:.1f}% ({i + batch_size} samples, {elapsed:.1f}s)")
        
        total_time = time.time() - start_time
        print(f"  Completed in {total_time:.2f} seconds")
        
        # Calculate expected distribution (uniform)
        expected = np.full(self.num_bins, n_samples / self.num_bins)
        
        # Calculate chi-square test statistic
        chi2 = np.sum((counts - expected)**2 / expected)
        
        # Degrees of freedom for chi-square test
        dof = self.num_bins - 1
        
        # Print chi-square results
        print(f"  Chi-square test: {chi2:.2f}, degrees of freedom: {dof}")
        print(f"  Mean samples per bin: {np.mean(counts):.2f}")
        print(f"  Standard deviation: {np.std(counts):.2f}")
        print(f"  Theoretical std dev: {np.sqrt(n_samples / self.num_bins):.2f}")
        
        # Plot histogram
        self._plot_distribution(counts, 'Mersenne Twister', 'mersenne_int')
        
        # Critical value for 99.9% confidence with 999 degrees of freedom
        # For 999 dof, we'll use the approximation sqrt(2 * dof) + 3.1
        critical_value = np.sqrt(2 * dof) + 3.1 * np.sqrt(dof)
        
        # Check if distribution is approximately uniform
        self.assertLess(chi2, critical_value)
        
    def test_numpy_distribution_int(self):
        """Test distribution of 100M integer samples with NumPy RNG."""
        print("\nTesting NumPy RNG distribution (100M samples)...")
        
        # Number of samples
        n_samples = 100_000_000
        batch_size = 1_000_000
        
        # Create bins
        bins = np.linspace(self.min_val, self.max_val + 1, self.num_bins + 1)
        counts = np.zeros(self.num_bins)
        
        # Generate samples in batches and bin them
        start_time = time.time()
        for i in range(0, n_samples, batch_size):
            batch = self.numpy_rng.get_batch_ints(self.min_val, self.max_val, batch_size)
            batch_counts, _ = np.histogram(batch, bins=bins)
            counts += batch_counts
            
            # Print progress
            if (i + batch_size) % 10_000_000 == 0:
                progress = (i + batch_size) / n_samples * 100
                elapsed = time.time() - start_time
                print(f"  Progress: {progress:.1f}% ({i + batch_size} samples, {elapsed:.1f}s)")
        
        total_time = time.time() - start_time
        print(f"  Completed in {total_time:.2f} seconds")
        
        # Calculate expected distribution (uniform)
        expected = np.full(self.num_bins, n_samples / self.num_bins)
        
        # Calculate chi-square test statistic
        chi2 = np.sum((counts - expected)**2 / expected)
        
        # Degrees of freedom for chi-square test
        dof = self.num_bins - 1
        
        # Print chi-square results
        print(f"  Chi-square test: {chi2:.2f}, degrees of freedom: {dof}")
        print(f"  Mean samples per bin: {np.mean(counts):.2f}")
        print(f"  Standard deviation: {np.std(counts):.2f}")
        print(f"  Theoretical std dev: {np.sqrt(n_samples / self.num_bins):.2f}")
        
        # Plot histogram
        self._plot_distribution(counts, 'NumPy RNG', 'numpy_int')
        
        # Critical value for 99.9% confidence with 999 degrees of freedom
        critical_value = np.sqrt(2 * dof) + 3.1 * np.sqrt(dof)
        
        # Check if distribution is approximately uniform
        self.assertLess(chi2, critical_value)
        
    def test_performance_comparison(self):
        """Compare performance of RNG strategies."""
        print("\nComparing RNG performance (10M samples)...")
        
        n_samples = 10_000_000
        
        # Test Mersenne Twister performance
        start_time = time.time()
        _ = self.mersenne_rng.get_batch_ints(self.min_val, self.max_val, n_samples)
        mersenne_time = time.time() - start_time
        
        print(f"  Mersenne Twister: {mersenne_time:.2f} seconds")
        
        # Test NumPy RNG performance
        start_time = time.time()
        _ = self.numpy_rng.get_batch_ints(self.min_val, self.max_val, n_samples)
        numpy_time = time.time() - start_time
        
        print(f"  NumPy RNG: {numpy_time:.2f} seconds")
        print(f"  Performance ratio: {mersenne_time / numpy_time:.2f}x")
        
    def _plot_distribution(self, counts: np.ndarray, title: str, filename: str):
        """Plot distribution histogram and save to file."""
        plt.figure(figsize=(12, 6))
        
        # Plot histogram
        x = np.linspace(self.min_val, self.max_val, self.num_bins)
        plt.bar(x, counts, width=(self.max_val - self.min_val) / self.num_bins, alpha=0.7)
        
        # Plot expected line
        expected = np.mean(counts)
        plt.axhline(y=expected, color='r', linestyle='-', alpha=0.7, 
                   label=f'Expected: {expected:.1f}')
        
        # Plot 3-sigma bounds
        std_dev = np.sqrt(expected)
        plt.axhline(y=expected + 3*std_dev, color='g', linestyle='--', alpha=0.5,
                   label=f'+3σ: {expected + 3*std_dev:.1f}')
        plt.axhline(y=expected - 3*std_dev, color='g', linestyle='--', alpha=0.5,
                   label=f'-3σ: {expected - 3*std_dev:.1f}')
        
        # Set labels and title
        plt.xlabel('Value')
        plt.ylabel('Frequency')
        plt.title(f'{title} Distribution - {self.num_bins} bins')
        plt.legend()
        
        # Set y-axis limits to focus on deviations
        margin = 5 * std_dev
        plt.ylim(expected - margin, expected + margin)
        
        # Save plot
        plot_path = os.path.join(self.output_dir, f'{filename}_distribution.png')
        plt.savefig(plot_path)
        print(f"  Plot saved to {plot_path}")
        plt.close()


if __name__ == "__main__":
    unittest.main()