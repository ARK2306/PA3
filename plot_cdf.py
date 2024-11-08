import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
from pathlib import Path

def analyze_multiple_producers(file_paths):
    """
    Analyze latency data from multiple producers given their CSV file paths.
    
    Args:
        file_paths (list): List of paths to the CSV files
    """
    if not file_paths:
        print("Error: No file paths provided")
        return
    
    print(f"Processing {len(file_paths)} producer result files")
    
    # Create plot
    plt.figure(figsize=(12, 8))
    
    # Use different colors for each producer
    colors = plt.cm.viridis(np.linspace(0, 1, len(file_paths)))
    
    # Store statistics for all producers
    all_stats = {}
    
    # Process each file
    for file_path, color in zip(sorted(file_paths), colors):
        try:
            if not os.path.exists(file_path):
                print(f"Warning: File not found: {file_path}")
                continue
                
            # Extract producer number from filename or use full name
            producer_name = os.path.basename(file_path)
            producer_id = producer_name.split('_')[2][:8]  # Get first 8 chars of UUID
            
            # Read data
            df = pd.read_csv(file_path)
            
            # Calculate statistics
            stats = {
                'mean': df['latency'].mean(),
                'median': df['latency'].median(),
                'std': df['latency'].std(),
                'min': df['latency'].min(),
                'max': df['latency'].max(),
                'p90': np.percentile(df['latency'], 90),
                'p95': np.percentile(df['latency'], 95),
                'p99': np.percentile(df['latency'], 99),
                'sample_size': len(df)
            }
            
            all_stats[producer_id] = stats
            
            # Calculate and plot CDF
            sorted_latencies = np.sort(df['latency'])
            cdf = np.arange(1, len(sorted_latencies) + 1) / len(sorted_latencies)
            
            # Plot CDF line
            plt.plot(sorted_latencies, cdf, 
                    label=f'Producer {producer_id}',
                    color=color, linewidth=2)
            
            # Add vertical lines for 90th and 95th percentiles
            plt.axvline(x=stats['p90'], color=color, linestyle='--', alpha=0.3)
            plt.axvline(x=stats['p95'], color=color, linestyle=':', alpha=0.3)
            
        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")
    
    # Customize plot
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.xlabel('Latency (seconds)')
    plt.ylabel('Cumulative Probability')
    plt.title('Latency CDF Comparison Across Producers')
    plt.legend()
    
    # Add some padding to the x-axis
    plt.xlim(left=0)
    plt.ylim(0, 1.05)
    
    # Enhance grid
    plt.grid(True, which='both', linestyle='--', alpha=0.7)
    
    # Use seaborn style for better visualization
    sns.set_style("whitegrid")
    
    plt.tight_layout()
    
    # Print statistics for each producer
    print("\nLatency Statistics by Producer (in seconds):")
    for producer_id, stats in all_stats.items():
        print(f"\nProducer {producer_id}:")
        print(f"Sample Size: {stats['sample_size']}")
        print(f"Mean Latency: {stats['mean']:.4f}")
        print(f"Median Latency: {stats['median']:.4f}")
        print(f"Standard Deviation: {stats['std']:.4f}")
        print(f"90th Percentile: {stats['p90']:.4f}")
        print(f"95th Percentile: {stats['p95']:.4f}")
        print(f"99th Percentile: {stats['p99']:.4f}")
        print(f"Min: {stats['min']:.4f}")
        print(f"Max: {stats['max']:.4f}")
    
    # Save plot
    plot_path = 'latency_cdf_comparison.png'
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    print(f"\nPlot saved as '{os.path.abspath(plot_path)}'")
    
    plt.show()
    return all_stats

if __name__ == "__main__":
    # Example usage with manual paths
    file_paths = [
"/Users/aryanreddy/Desktop/PA3/results/producers-5/results_producer_71c6fafd-cbb4-4a03-ab61-1f4582bc170c.csv",
" /Users/aryanreddy/Desktop/PA3/results/producers-5/results_producer_436a24b7-7348-4bf5-9ccc-e4da222fa891.csv ",
" /Users/aryanreddy/Desktop/PA3/results/producers-5/results_producer_a98f6906-34ef-4a3c-b30f-622b7fd9874c.csv ",
"/Users/aryanreddy/Desktop/PA3/results/producers-5/results_producer_b3502f80-e47f-4fee-9111-b8927f2c607e.csv",
"/Users/aryanreddy/Desktop/PA3/results/producers-5/results_producer_ca7700a1-ea73-4d67-84b4-efb99f1d4449.csv"
    ]
    
    # You can modify these paths to match your actual file locations
    analyze_multiple_producers(file_paths)