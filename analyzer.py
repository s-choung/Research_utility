import os
import numpy as np
from ase.dft import get_distribution_moment
import pandas as pd
from utils import sum_spins, sum_spins_orbitals


range_columns = ['s', 'p', 'd']


def analyze_file(file, orbital_type):
    # Load DOSCAR data, skipping the first line
    data = np.loadtxt(file, skiprows=1)

    # Sum spins up and down
    data = sum_spins(data)

    # Extract energy column
    e = data[:, 0]

    # Range of columns and sum spins orbitals
    data = sum_spins_orbitals(data, 1)

    # Compute moments for the orbital type
    d = data[:, range_columns.index(orbital_type)+1]
    center = get_distribution_moment(e, d, 1)

    results = {
        'file': file,
        'orbital': orbital_type,
        'center': round(center, 2),
    }

    if orbital_type == 'd':
        width = get_distribution_moment(e, d, 2)
        # Calculate filling
        total_integral = np.trapz(d, e)
        negative_energy_mask = e < 0
        negative_energy_integral = np.trapz(d[negative_energy_mask], e[negative_energy_mask])
        filling = negative_energy_integral / total_integral

        results.update({
            'width': round(width, 2),
            'filling': round(filling, 2)
        })

    return results

# Define the root directory where your folders start
root_dir = './'

# Create an empty DataFrame to store the results
df = pd.DataFrame(columns=['file', 'orbital', 'center', 'width', 'filling'])
results_dict = {}
# Walk through all directories and subdirectories from root_dir
for dirpath, dirnames, filenames in os.walk(root_dir):
    # If any of the files you want to analyze are in the filenames
    if dirpath not in results_dict:
        results_dict[dirpath] = []
    for part in range(1, 6):
        for file_name in filenames:
            if 'doscar_part_{}.lobster'.format(part) in file_name:
                # Define full file path
                file_path = os.path.join(dirpath, file_name)

                # Define orbital type to analyze
                orbital_type = 'd' if part == 5 else 'sp'[part % 2]

                # Analyze the file and add the results to the Dictionary
                results = analyze_file(file_path, orbital_type)
                if 'width' in results and 'filling' in results:
                 results_dict[dirpath].extend([results['center'], results['width'], results['filling']])
                else:
                 results_dict[dirpath].extend([results['center'], None, None])
df = pd.DataFrame.from_dict(results_dict, orient='index')
# Save the DataFrame to a CSV file
df.to_csv('dos_results.csv', index=False)

