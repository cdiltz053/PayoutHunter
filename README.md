# PayoutHunter

This repository contains the Python script for the Payout Link Hunter, designed to run 24/7 on a dedicated machine using a **GitHub Actions Self-Hosted Runner** for continuous, cost-free operation.

## 🚀 24/7 Deployment Guide (Self-Hosted Runner)

To get this script running 24/7 on your old Gateway laptop, you need to set it up as a GitHub Actions Self-Hosted Runner.

### Prerequisites

1.  **Operating System:** Your laptop should be running a modern Linux distribution (e.g., Ubuntu, Debian) or macOS. Windows can also work, but the instructions below are for Linux/macOS.
2.  **Software:** You need to have `git`, `python3`, `pip`, and `screen` installed.

### Step 1: Set up GitHub Secrets

For security, you must add your Pushover credentials as **Secrets** in your GitHub repository settings. This prevents your keys from being exposed in the code.

1.  Go to your repository on GitHub: `https://github.com/cdiltz053/PayoutHunter`
2.  Click on **Settings** -> **Secrets and variables** -> **Actions**.
3.  Click **New repository secret** and add the following two secrets:
    *   **Name:** `PUSHOVER_USER`
    *   **Value:** `uthdrjggurywppdc33k5y49nkeegqe` (Your Pushover User Key)
4.  Click **New repository secret** again and add:
    *   **Name:** `PUSHOVER_TOKEN`
    *   **Value:** `akwpdxg8sgshj353wz3xdgfmfjbhez` (Your Pushover App Token)

### Step 2: Set up the Self-Hosted Runner on Your Laptop

This process registers your laptop with GitHub so the deployment workflow can run on it.

1.  **Create a folder** for the runner on your laptop:
    ```bash
    mkdir actions-runner && cd actions-runner
    ```

2.  **Download the runner package** (replace `linux-x64` with `osx-x64` if you use macOS):
    ```bash
    # For Linux:
    curl -o actions-runner-linux-x64-2.316.0.tar.gz -L https://github.com/actions/runner/releases/download/v2.316.0/actions-runner-linux-x64-2.316.0.tar.gz
    # For macOS:
    # curl -o actions-runner-osx-x64-2.316.0.tar.gz -L https://github.com/actions/runner/releases/download/v2.316.0/actions-runner-osx-x64-2.316.0.tar.gz
    
    tar xzf actions-runner-*.tar.gz
    ```

3.  **Configure the runner:**
    *   Go to your repository settings on GitHub: `https://github.com/cdiltz053/PayoutHunter/settings/actions/runners`
    *   Click **New self-hosted runner** and follow the on-screen instructions to get your unique configuration token.
    *   Run the following commands in your laptop's terminal, replacing the URL and token with the values provided by GitHub:
        ```bash
        # Example from GitHub - use your actual URL and Token
        ./config.sh --url https://github.com/cdiltz053/PayoutHunter --token YOUR_TOKEN_HERE
        ```
    *   For the runner name, you can use `Gateway-Laptop`.

4.  **Run the runner application:**
    ```bash
    ./run.sh
    ```
    **Keep this terminal window open and the laptop running 24/7.** This application listens for deployment jobs from GitHub.

### Step 3: Run the Deployment Workflow

Now that your laptop is listening, you can trigger the deployment from GitHub.

1.  Go to the **Actions** tab in your repository.
2.  Select the **Deploy and Run Payout Hunter** workflow.
3.  Click **Run workflow** on the right side.
4.  The workflow will:
    *   Clone the repository to your laptop.
    *   Install dependencies.
    *   Start the `payout_hunter.py` script inside a detached `screen` session named `payout-hunter`.

### 🔍 Checking the Script Status

To see the script's output and confirm it's running:

1.  In your laptop's terminal, run:
    ```bash
    screen -r payout-hunter
    ```
2.  To detach and leave it running in the background, press **Ctrl+A** then **D**.

---
*Created by Manus AI*
