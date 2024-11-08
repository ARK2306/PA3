import pandas as pd
import matplotlib.pyplot as plt
import glob
import os
import numpy as np

def plot_cdf():
    # Create a figure with a larger size
    plt.figure(figsize=(10, 6))
    
    # Read all CSV files in the current directory
    csv_files = glob.glob('*.csv')
    
    if not csv_files:
        print("No CSV files found!")
        return
        
    # Combine results from all files
    dfs = []
    for file in csv_files:
        df = pd.read_csv(file)
        dfs.append(df)
    
    combined_df = pd.concat(dfs)
    
    # Calculate CDF
    latencies = combined_df['latency'].sort_values()
    y_vals = np.arange(1, len(latencies) + 1) / len(latencies)
    
    # Plot CDF
    plt.plot(latencies, y_vals, label=f'{len(csv_files)} Producers', linewidth=2)
    
    # Calculate statistics
    stats = combined_df['latency'].describe()
    print("\nLatency Statistics:")
    print(f"Mean latency: {stats['mean']:.4f} seconds")
    print(f"Median latency: {stats['50%']:.4f} seconds")
    print(f"95th percentile: {combined_df['latency'].quantile(0.95):.4f} seconds")
    print(f"99th percentile: {combined_df['latency'].quantile(0.99):.4f} seconds")
    
    plt.grid(True, alpha=0.3)
    plt.xlabel('Latency (seconds)', fontsize=12)
    plt.ylabel('Cumulative Probability', fontsize=12)
    plt.title('CDF of End-to-End Latency', fontsize=14)
    plt.legend()
    
    # Save plot
    plt.savefig('latency_cdf.png')
    print("\nPlot saved as latency_cdf.png")
    plt.close()

if __name__ == "__main__":
    plot_cdf()
