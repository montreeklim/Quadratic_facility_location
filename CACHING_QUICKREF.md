# Quick Reference - Result Caching System

## One-Time Setup
```bash
cd src/models
python solve_and_cache_models.py --region Hampshire --instance 1
```

## Subsequent Runs
```bash
python create_hampshire_tables.py      # Fast!
python create_hampshire_figures.py     # Fast!
```

---

## Common Commands

### List what's cached
```python
from result_cache import list_cached_results
list_cached_results('own_results/model_cache')
```

### Clear cache
```python
from result_cache import clear_cache
clear_cache('own_results/model_cache', 'Hampshire')  # Clear Hampshire only
clear_cache('own_results/model_cache')               # Clear all
```

### Force re-solving
```bash
python solve_and_cache_models.py --region Hampshire --instance 1 --no-skip
```

### Disable cache for one function
```python
from figures_and_tables import create_figure3a
create_figure3a(..., use_cache=False)
```

### Disable cache globally
Edit `figures_and_tables.py`, line 20:
```python
USE_CACHE = False
```

---

## File Locations

| Item | Location |
|------|----------|
| Cache | `own_results/model_cache/` |
| Source code | `src/models/` |
| Pre-solver | `solve_and_cache_models.py` |
| Main functions | `figures_and_tables.py` |
| Core cache module | `result_cache.py` |
| Documentation | `CACHING_README.md` |
| Examples | `example_caching.py` |

---

## How It Works

1. **Before:** `solve_model_naively()` called 8+ times per figure (slow)
2. **After:** Results loaded from cache (instant!)

```
Without Cache:
  create_figure → solve_model_naively → 10 min × 8 models = 80 min total

With Cache:
  create_figure → load_from_cache → 0.1 sec × 8 models = 0.8 sec total
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Cache not used | Run `solve_and_cache_models.py` first |
| Still slow | Check `[CACHE]` messages in console |
| Cache errors | `clear_cache()` then re-run pre-solver |
| Cache too large | `clear_cache()` to remove old results |

---

## Cache Files

Each file in `own_results/model_cache/` contains:
- Model parameters (budget, cutoff, etc.)
- Solution (assignments, open facilities)
- Metrics (access, utilization, fairness)
- Metadata (solve time, bounds)

Files are named with MD5 hash of parameters:
- `result_a1b2c3d4.json` ← Same budget/params = Same file

---

## Next Steps

1. Run pre-solver: `python solve_and_cache_models.py --region Hampshire --instance 1`
2. Generate tables: `python create_hampshire_tables.py`
3. Generate figures: `python create_hampshire_figures.py`

For detailed info: See `CACHING_README.md` in `src/models/`
