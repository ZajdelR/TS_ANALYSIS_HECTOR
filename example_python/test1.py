import subprocess

def run_in_wsl(command):
    """Run a command in WSL and return its output"""
    result = subprocess.run(
        ["wsl", "-e", "bash", "-c", command],
        capture_output=True,
        text=True
    )
    return result.stdout, result.stderr

# Example usage
station = "TEST"
noise_model = "WN"
freq = "0.0"
wsl_path = "/mnt/c/Users/rados/Documents/VM_SHARED/PYTHON/HECTOR/hector-2.1_source/test1/"

# Set up file structure
subprocess.run(["wsl", "-e", "mkdir", "-p", f"{wsl_path}/obs_files"])
subprocess.run(["wsl", "-e", "mkdir", "-p", f"{wsl_path}/pre_files"])
subprocess.run(["wsl", "-e", "mkdir", "-p", f"{wsl_path}/mom_files"])

# Copy the script to WSL
subprocess.run(["wsl", "-e", "cp", "analyse_timeseries.py", f"{wsl_path}/"])

# Run the script in WSL
command = f"cd {wsl_path} && ./analyse_timeseries.py -s {station} -n {noise_model} -f {freq}"
stdout, stderr = run_in_wsl(command)
print(stdout)