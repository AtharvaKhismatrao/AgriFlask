import itertools
import pickle
import pandas as pd
import numpy as np

SF={
    'low':{'N':35.0,'P':30.0,'K':30.0},
    'medium':{'N':65.0,'P':55.0,'K':50.0},
    'high':{'N':95.0,'P':75.0,'K':70.0}
}
ST={
    'sandy':{'N':-10.0,'P':-5.0,'K':-10.0},
    'loamy':{'N':0.0,'P':0.0,'K':0.0},
    'clayey':{'N':5.0,'P':5.0,'K':10.0},
    'silty':{'N':3.0,'P':4.0,'K':5.0}
}
AP={'normal':6.8,'white_crust':8.1,'very_dark':6.3,'sticky_clay':7.4,'not_sure':6.8}
AH={'very_dry':30.0,'dry':45.0,'comfortable':60.0,'humid':75.0,'very_humid':90.0}
RF={'very_low':20.0,'light':40.0,'moderate':90.0,'heavy':180.0,'very_heavy':280.0}
TP={'cool':18.0,'mild':25.0,'warm':31.0,'hot':38.0}

def clamp(v, lo, hi):
    return max(lo, min(v, hi))

with open('crop_model.pkl', 'rb') as f:
    m = pickle.load(f)

rows=[]
for t,f,a,h,r,temp in itertools.product(ST, SF, AP, AH, RF, TP):
    b=SF[f]
    ad=ST[t]
    N=clamp(b['N']+ad['N'],10,120)
    P=clamp(b['P']+ad['P'],10,110)
    K=clamp(b['K']+ad['K'],10,180)

    X = pd.DataFrame([{
        'N':N,
        'P':P,
        'K':K,
        'temperature':TP[temp],
        'humidity':AH[h],
        'ph':AP[a],
        'rainfall':RF[r]
    }])

    probs = m.predict_proba(X)[0]
    idx = np.argsort(probs)[::-1]
    c = float(probs[idx[0]])
    c2 = float(probs[idx[1]]) if len(idx) > 1 else 0.0

    rows.append({
        'crop': m.classes_[idx[0]],
        'conf': c,
        'margin': c-c2,
        'soil_texture': t,
        'soil_fertility': f,
        'soil_appearance': a,
        'air_humidity': h,
        'rainfall_pattern': r,
        'temperature_feel': temp,
        'N': N, 'P': P, 'K': K,
        'temperature': TP[temp],
        'humidity': AH[h],
        'ph': AP[a],
        'rainfall': RF[r],
    })

rows.sort(key=lambda x: (x['conf'], x['margin']), reverse=True)
print('TOTAL', len(rows))
print('TOP25')
for r in rows[:25]:
    print(
        f"{r['crop']}|{r['conf']*100:.1f}|{r['margin']*100:.1f}|"
        f"{r['soil_texture']},{r['soil_fertility']},{r['soil_appearance']},{r['air_humidity']},{r['rainfall_pattern']},{r['temperature_feel']}|"
        f"NPK={r['N']:.0f},{r['P']:.0f},{r['K']:.0f};temp={r['temperature']:.0f};hum={r['humidity']:.0f};ph={r['ph']:.1f};rain={r['rainfall']:.0f}"
    )

print('BEST_PER_CROP')
best = {}
for r in rows:
    if r['crop'] not in best:
        best[r['crop']] = r
for crop in sorted(best):
    r = best[crop]
    print(
        f"{crop}|{r['conf']*100:.1f}|{r['margin']*100:.1f}|"
        f"{r['soil_texture']},{r['soil_fertility']},{r['soil_appearance']},{r['air_humidity']},{r['rainfall_pattern']},{r['temperature_feel']}|"
        f"NPK={r['N']:.0f},{r['P']:.0f},{r['K']:.0f};temp={r['temperature']:.0f};hum={r['humidity']:.0f};ph={r['ph']:.1f};rain={r['rainfall']:.0f}"
    )
