"""
Diagnosis: compute MCC, balanced accuracy, and AP per matchup.
Also optimize weights via grid search on train games, test on held-out.
"""
import numpy as np
from sklearn.metrics import (matthews_corrcoef, balanced_accuracy_score,
                             average_precision_score, f1_score,
                             roc_auc_score)
from scipy.optimize import differential_evolution
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

# ── Copy game/policy code inline (avoids import issues) ──────────────────
from dataclasses import dataclass
from typing import Tuple, List

@dataclass
class State:
    px: int; py: int; rx: int; ry: int; turn: int
    def distance(self): return abs(self.px-self.rx)+abs(self.py-self.ry)
    def is_terminal(self): return self.distance()==0
    def __hash__(self): return hash((self.px,self.py,self.rx,self.ry,self.turn))
    def __eq__(self,o): return (self.px,self.py,self.rx,self.ry,self.turn)==(o.px,o.py,o.rx,o.ry,o.turn)

class Game:
    def __init__(self,size=4): self.size=size
    def get_legal_moves(self,state):
        moves=[(0,0),(1,0),(-1,0),(0,1),(0,-1)]
        x,y=(state.px,state.py) if state.turn==0 else (state.rx,state.ry)
        return [(dx,dy) for dx,dy in moves if 0<=x+dx<self.size and 0<=y+dy<self.size]
    def apply_move(self,state,move):
        dx,dy=move
        if state.turn==0: return State(state.px+dx,state.py+dy,state.rx,state.ry,1)
        return State(state.px,state.py,state.rx+dx,state.ry+dy,0)
    def ground_truth_stagnation(self,history):
        n=len(history); stag=[0]*n
        if n<2: return stag
        pd=[]
        for t in range(1,n):
            prev,curr=history[t-1],history[t]; S=0
            if curr==prev: S=1
            elif prev.turn==1:
                if abs(curr.rx-prev.rx)+abs(curr.ry-prev.ry)>0:
                    if curr.distance()>=prev.distance(): S=1
            if prev.turn==0:
                pd.append(curr.distance())
                if len(pd)>3: pd=pd[-3:]
                if curr.distance()<prev.distance(): S=0
            if prev.turn==0 and len(pd)>=3:
                if all(d>=pd[0] for d in pd[1:]): S=1
            stag[t]=S
        return stag
    def components(self,state,prev):
        pm=len(self.get_legal_moves(prev)); cm=len(self.get_legal_moves(state))
        I=max(0,(cm-pm)/16.0)
        Thr=max(0,(prev.distance()-state.distance())/6.0)
        P=1 if state.distance()<prev.distance() else 0
        E=(prev.distance()-state.distance())/6.0
        S=1 if state==prev else 0
        return np.array([I,Thr,P,E,0.0,0.0,S])  # R=A=0

class PP:
    def get_move(self,state,moves):
        best=(0,0); bd=state.distance()
        for m in moves:
            ns=Game().apply_move(state,m)
            if ns.distance()<bd: bd=ns.distance(); best=m
        return best
class SP:
    def get_move(self,state,moves):
        worst=(0,0); wd=-1
        for m in moves:
            ns=Game().apply_move(state,m)
            if ns.distance()>wd: wd=ns.distance(); worst=m
        return worst
class RP:
    def get_move(self,state,moves): return moves[np.random.randint(len(moves))]
class ER:
    def get_move(self,state,moves):
        best=(0,0); bd=-1
        for m in moves:
            ns=Game().apply_move(state,m)
            if ns.distance()>bd: bd=ns.distance(); best=m
        return best

def run_game(game,pp,pr,max_steps=100):
    state=State(0,0,3,3,0); history=[state]
    for _ in range(max_steps):
        if state.is_terminal(): break
        moves=game.get_legal_moves(state)
        move=(pp if state.turn==0 else pr).get_move(state,moves)
        state=game.apply_move(state,move); history.append(state)
    return history

def collect(game,pp,pr,n,seed):
    np.random.seed(seed)
    comps,labels=[],[]
    for _ in range(n):
        h=run_game(game,pp,pr)
        sg=game.ground_truth_stagnation(h)
        for t in range(1,len(h)):
            comps.append(game.components(h[t],h[t-1]))
            labels.append(sg[t])
    return np.array(comps),np.array(labels)

def score(w,comps,labels,theta=0.05):
    w7=np.array([w[0],w[1],w[2],w[3],w[4],w[5],-w[6]])
    lh=comps@w7
    pred=(lh<=theta).astype(int)
    if pred.sum()==0 or pred.sum()==len(pred): return 0.0
    return matthews_corrcoef(labels,pred)

# ── Main ─────────────────────────────────────────────────────────────────
game=Game()
THETA=0.05
W_chess=np.array([0.15,0.25,0.20,0.15,0.05,0.10,0.10])

matchups=[
    ('ProductiveP vs RandomR', PP(), RP()),
    ('SterileP vs EscapingR',  SP(), ER()),
    ('RandomP vs EscapingR',   RP(), ER()),
    ('ProductiveP vs EscapingR',PP(),ER()),
]

print("="*75)
print("Stagnation Grid — full diagnosis (chess weights vs calibrated weights)")
print("="*75)

all_comps={}; all_labels={}
for name,pp,pr in matchups:
    c,l=collect(game,pp,pr,100,42)
    all_comps[name]=c; all_labels[name]=l

# ── Per-matchup: chess weights ────────────────────────────────────────────
print("\n── Chess weights (w=[0.15,0.25,0.20,0.15,0.05,0.10,-0.10]) ──")
print(f"{'Matchup':<28} {'GT%':>5} {'AUC':>6} {'AP':>6} {'MCC':>6} {'BalAcc':>7}")
print("-"*62)
for name,pp,pr in matchups:
    c,l=all_comps[name],all_labels[name]
    w7=np.array([0.15,0.25,0.20,0.15,0.05,0.10,-0.10])
    lh=c@w7; pred=(lh<=THETA).astype(int)
    try: auc=roc_auc_score(l,-lh)
    except: auc=float('nan')
    try: ap=average_precision_score(l,-lh)
    except: ap=float('nan')
    mcc=score(W_chess,c,l)
    ba=balanced_accuracy_score(l,pred)
    print(f"{name:<28} {100*l.mean():>4.1f}% {auc:>6.3f} {ap:>6.3f} {mcc:>6.3f} {ba:>7.3f}")

# ── Weight optimization on training split ─────────────────────────────────
print("\n── Weight optimization (train on 60 games, test on 40 games) ──")

def neg_mcc_train(w, name):
    c_tr=all_comps_tr[name]; l_tr=all_labels_tr[name]
    return -score(np.abs(w), c_tr, l_tr)

all_comps_tr={}; all_labels_tr={}
all_comps_te={}; all_labels_te={}

for name,pp,pr in matchups:
    c60,l60=collect(game,pp,pr,60,42)   # train
    c40,l40=collect(game,pp,pr,40,123)  # test (different seed)
    all_comps_tr[name]=c60; all_labels_tr[name]=l60
    all_comps_te[name]=c40; all_labels_te[name]=l40

print(f"{'Matchup':<28} {'GT%':>5} {'AP(chess)':>10} {'AP(opt)':>8} {'MCC(opt)':>9} {'BalAcc(opt)':>11}")
print("-"*78)

for name,pp,pr in matchups:
    c_te=all_comps_te[name]; l_te=all_labels_te[name]

    # chess baseline on test
    w7=np.array([0.15,0.25,0.20,0.15,0.05,0.10,-0.10])
    lh_chess=c_te@w7
    try: ap_chess=average_precision_score(l_te,-lh_chess)
    except: ap_chess=float('nan')

    # optimise on train
    bounds=[(0,1)]*7
    res=differential_evolution(neg_mcc_train,bounds,args=(name,),
                               seed=42,maxiter=200,tol=1e-4,
                               popsize=15,mutation=(0.5,1.5),recombination=0.7,
                               disp=False)
    w_opt=np.abs(res.x)

    # evaluate on test
    w7_opt=np.array([w_opt[0],w_opt[1],w_opt[2],w_opt[3],w_opt[4],w_opt[5],-w_opt[6]])
    lh_opt=c_te@w7_opt
    pred_opt=(lh_opt<=THETA).astype(int)
    try: ap_opt=average_precision_score(l_te,-lh_opt)
    except: ap_opt=float('nan')
    mcc_opt=matthews_corrcoef(l_te,pred_opt) if pred_opt.std()>0 else 0.0
    ba_opt=balanced_accuracy_score(l_te,pred_opt)

    w_fmt=' '.join(f'{v:.2f}' for v in w_opt)
    print(f"{name:<28} {100*l_te.mean():>4.1f}% {ap_chess:>10.3f} {ap_opt:>8.3f} {mcc_opt:>9.3f} {ba_opt:>11.3f}")
    print(f"  opt weights: [{w_fmt}]")

# ── Pooled non-degenerate: ProductiveP + RandomP ─────────────────────────
print("\n── Pooled (ProductiveP + RandomP, chess weights, test set) ──")
c_pool=np.vstack([all_comps_te['ProductiveP vs RandomR'],
                  all_comps_te['RandomP vs EscapingR']])
l_pool=np.concatenate([all_labels_te['ProductiveP vs RandomR'],
                       all_labels_te['RandomP vs EscapingR']])
w7=np.array([0.15,0.25,0.20,0.15,0.05,0.10,-0.10])
lh_p=c_pool@w7
print(f"  n={len(l_pool)}, GT%={100*l_pool.mean():.1f}%")
print(f"  AUC={roc_auc_score(l_pool,-lh_p):.3f}")
print(f"  AP ={average_precision_score(l_pool,-lh_p):.3f}")
pred_p=(lh_p<=THETA).astype(int)
print(f"  MCC={matthews_corrcoef(l_pool,pred_p):.3f}")
print(f"  BalAcc={balanced_accuracy_score(l_pool,pred_p):.3f}")
print("\nDone.")
