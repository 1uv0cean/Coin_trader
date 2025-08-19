import pandas as pd
from test_optimizer import StrategyOptimizer

def create_test_data(output_path: str = "test_data.csv", periods: int = 5000):
    """
    Generates a sample CSV file for backtesting.
    """
    print(f"Generating sample data with {periods} periods...")

    # generate_sample_data is now a static method, so we can call it directly.
    df = StrategyOptimizer.generate_sample_data(periods=periods)

    df.to_csv(output_path, index=False)
    print(f"Sample data saved to {output_path}")

if __name__ == "__main__":
    create_test_data()
