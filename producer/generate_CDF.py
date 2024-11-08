import pandas as pd
import matplotlib.pyplot as plt
import glob
import numpy as np

def plot_cdf():
    # Get all result files
    result_files = glob.glob('/opt/producer-results/latency_results_producer_*.csv')
    
    plt.figure(figsize=(10, 6))
    
    for file in result_files:
        df = pd.read_csv(file)
        latencies = df['Latency (seconds)'].sort_values()
        
        # Calculate CDF
        y_vals = np.arange(len(latencies)) / float(len(latencies))
        
        # Plot CDF
        plt.plot(latencies, y_vals, label=f'Producer {file.split("_")[-1].split(".")[0]}')
    
    plt.xlabel('Latency (seconds)')
    plt.ylabel('CDF')
    plt.title('Latency CDF for Different Numbers of Producers')
    plt.legend()
    plt.grid(True)
    plt.savefig('/opt/producer-results/latency_cdf.png')
    plt.close()

if __name__ == "__main__":
    plot_cdf()
