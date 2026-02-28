import numpy as np
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt
from pathlib import Path

def willingness_model(d, a, b, c):
    """
    Calculates the willingness to travel a given distance based on the model:
    P(d) = a * exp(-b * d^c)
    """
    return a * np.exp(-b * d**c)

def calculate_r_squared(y_true, y_pred):
    """Calculates the R-squared value for the fit."""
    residuals = y_true - y_pred
    ss_res = np.sum(residuals**2)
    ss_tot = np.sum((y_true - np.mean(y_true))**2)

    if ss_tot == 0:
        return 1.0 if ss_res == 0 else 0.0

    return 1 - (ss_res / ss_tot)

# --- 1. Data Preparation ---
d_urban = np.array([0, 1, 2, 5, 10, 25, 50, 100])
p_urban = np.array([1.00, 0.73, 0.53, 0.25, 0.12, 0.03, 0.02, 0.01])
d_rural = np.array([0, 1, 2, 5, 10, 25, 50, 100])
p_rural = np.array([1.00, 0.76, 0.61, 0.41, 0.22, 0.07, 0.03, 0.01])

# --- 2. Curve Fitting ---
params_urban, _ = curve_fit(willingness_model, d_urban, p_urban, p0=[1, 0.1, 1], maxfev=5000)
p_urban_pred = willingness_model(d_urban, *params_urban)
r2_urban = calculate_r_squared(p_urban, p_urban_pred)

params_rural, _ = curve_fit(willingness_model, d_rural, p_rural, p0=[1, 0.1, 1], maxfev=5000)
p_rural_pred = willingness_model(d_rural, *params_rural)
r2_rural = calculate_r_squared(p_rural, p_rural_pred)

# --- 3. Plotting ---

plt.style.use('seaborn-v0_8-whitegrid')
plt.figure(figsize=(13, 8))

urban_color = 'royalblue'
rural_color = 'darkorange'

plt.scatter(d_urban, p_urban, label='Urban Actual Data', color=urban_color, s=60, zorder=5, alpha=0.8, edgecolors='w')
plt.scatter(d_rural, p_rural, label='Rural Actual Data', color=rural_color, s=80, zorder=5, marker='X', alpha=0.9, edgecolors='w')

d_fit = np.linspace(0, 100, 400)

p_fit_urban = willingness_model(d_fit, *params_urban)
plt.plot(d_fit, p_fit_urban, color=urban_color, linewidth=2.5, label=f'Urban Fitted Model (R²={r2_urban:.3f})')
p_fit_rural = willingness_model(d_fit, *params_rural)
plt.plot(d_fit, p_fit_rural, color=rural_color, linewidth=2.5, label=f'Rural Fitted Model (R²={r2_rural:.3f})')

# --- 4. Add Equations to the Plot ---
urban_eq = (f'$P_{{urban}}(d) = {params_urban[0]:.3f} \\cdot e^{{-{params_urban[1]:.3f} \\cdot d^{{{params_urban[2]:.3f}}}}}$')
rural_eq = (f'$P_{{rural}}(d) = {params_rural[0]:.3f} \\cdot e^{{-{params_rural[1]:.3f} \\cdot d^{{{params_rural[2]:.3f}}}}}$')

equation_text = f"Model Equations:\n{urban_eq}\n{rural_eq}"
plt.text(0.95, 0.7, equation_text, fontsize=12, transform=plt.gca().transAxes,
         ha='right', va='top',
         bbox=dict(boxstyle='round,pad=0.5', fc='aliceblue', ec='lightgray', alpha=0.9))

# --- 5. Final Plot Customization ---
plt.title('Willingness to Travel in Urban vs. Rural Areas', fontsize=16, fontweight='bold')
plt.xlabel('Distance (miles)', fontsize=12)
plt.ylabel('Willingness P(d)', fontsize=12)
plt.legend(loc='upper right', fontsize=11)
plt.ylim(0, 1.1)
plt.xlim(-2, 102)

# Save the final figure to the repo-level own_results directory
results_dir = Path(__file__).resolve().parents[2] / 'own_results'
results_dir.mkdir(parents=True, exist_ok=True)
output_path = results_dir / 'urban_vs_rural_willingness.png'
plt.savefig(output_path)
plt.show()