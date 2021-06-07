from charm.toolbox.pairinggroup import PairingGroup,ZR,G1,G2,GT,pair
from charm.toolbox.secretutil import SecretUtil
from charm.toolbox.ABEnc import Input, Output
from secretshare import SecretShare
from charm.core.engine.util import serializeDict,objectToBytes
import random
from datetime import datetime
from openpyxl import load_workbook
from openpyxl import Workbook
from PoK import PoK

mpk_t = { 'g':G1, 'h':G2, 'pp': G2, 'e_gh':GT, 'e_Xh':GT, 'vk':G2 , 'X': G1 }
msk_t = { 'sec':ZR, 'sgk':ZR }
pk_t = { 'pk':G2, 'Merlist':str }
sk_t = { 'shares': ZR }
Col_t = { 'PRFkey': ZR, 'key':G1, 'R':G2, 'S':G1, 'T':G1, 'W':G1 }
Rand_t = {'Rprime':G2, 'Sprime':G1, 'Tprime':G1, 'Wprime':G1}
ct_t = { 'C':GT, 'C1':GT, 'R':GT}
proof_t = {'z': ZR, 't': GT, 'y': GT}
proof1_t = {'z1': ZR, 'z2': ZR, 't': GT, 'y': GT}
prf_t= {'H':G1, 't':G1, 'c':ZR, 'r':ZR}

class Nirvana():
    def __init__(self, groupObj):
        global util, group
        util = SecretUtil(groupObj)
        group = groupObj
    
    @Output(mpk_t, msk_t)    
    def Setup(self):
        g, h, sec, sgk = group.random(G1), group.random(G2), group.random(ZR), group.random(ZR)
        g.initPP(); h.initPP()
        pp = h ** sec; e_gh = pair(g,h)
        vk = h ** sgk; X = group.random(G1); e_Xh=pair(X,h)
        mpk = {'g':g, 'h':h, 'pp':pp, 'e_gh':e_gh, 'e_Xh':e_Xh, 'vk': vk, 'X': X}
        msk = {'sec':sec, 'sgk':sgk }
        return (mpk, msk)

    @Input(mpk_t, msk_t, [str])
    @Output(pk_t, sk_t)
    def Keygen(self, mpk, msk, Merchants):
        pkey = {}
        shares = SSS.genShares(msk['sec'], 2, len(Merchants))
        for i in range(len(shares)-1):
            pkey[i] = mpk['h'] ** shares[i+1]
        pk = {'pk': pkey, 'Merlist': Merchants}
        sk = {'shares':shares}
        return (pk, sk)

    @Input(mpk_t, msk_t, int)
    @Output(Col_t)
    def Registeration(self, mpk, msk, n):
        PRFkey={}; key={}; S={}; T={}; t=group.random(ZR)
        for i in range(n):
            PRFkey[i] = group.random(ZR)
            key[i]= mpk['g'] ** PRFkey[i]
            S[i] = (key[i] ** (msk['sgk']/t)) * (mpk['X']**(1/t))
            T[i] = (S[i] ** (msk['sgk']/t)) * (mpk['g']**(1/t))
        R = mpk['h']**t
        W = mpk['g']**(1/t)
        return { 'PRFkey': PRFkey, 'key': key, 'R':R, 'S':S, 'T':T, 'W':W }

    @Input(mpk_t, Col_t, pk_t, ZR, int, int, ZR, GT)
    @Output(ct_t,Rand_t,proof_t,proof_t,proof_t,proof1_t)
    def Spending(self, mpk, Col, pk, time, d ,N, IDsk,ID):
        SAgg=1; TAgg=1; PRFkey=0; R=[]; X=[]; y2=1
        if len(Col['PRFkey']) >= d:
            for i in range(d):
                SAgg *= Col['S'][i]
                TAgg *= Col['T'][i]
                PRFkey += Col['PRFkey'][i]
                R.append(mpk['e_gh'] ** (1/(Col['PRFkey'][i]+time)))
                X.append(Col['PRFkey'][i])
                y2 *= R[i] ** X[i]
                A = pair(mpk['g'],mpk['vk']) ** PRFkey
            tprime = group.random(ZR)
            Rprime = Col['R'] ** (1/tprime)
            Sprime = SAgg ** tprime
            Tprime = (TAgg ** (tprime**2))* (Col['W']**(d*tprime*(1-tprime)))
            Wprime = Col['W'] ** (1/tprime)
            r = mpk['g'] ** (1/(PRFkey+time))
            C = ID * (pair(r, mpk['pp']))
            C1 = pair(r, pk['pk'][N])
            (proof1) = PoK.prover1(mpk['g'],A,PRFkey,mpk['vk']) #Proof of SPS
            (proof2) = PoK.prover4(y2,X,R) # Proof of Aggeragetd collatorals
            (proof3) = PoK.prover3(r,C1**PRFkey,PRFkey,pk['pk'][N]) #Proof of ciphertext C1
            (proof4) = PoK.prover2(C,mpk['e_gh'],((C/ID)**PRFkey)*(mpk['e_gh']**(-time*IDsk)),PRFkey,(-time*IDsk)) #Proof of ciphertext C0
            Rand = { 'Rprime':Rprime, 'Sprime':Sprime, 'Tprime':Tprime, 'Wprime':Wprime }
            ct = { 'C': C, 'C1': C1, 'R':R }
            return (ct, Rand, proof1, proof2, proof3, proof4)
        else:
            return (print("You don't have enough money in your account"), None)


    @Input(mpk_t, Col_t, pk_t, ZR, int, int, ZR, GT, ZR, list, GT)
    @Output(ct_t,proof_t,proof_t,proof_t,proof1_t)
    def PPSpending(self, mpk, Col, pk, time, d ,N, IDsk, ID, PRFkey, X, A):
        R=[]; y2=1
        if len(Col['PRFkey']) >= d:
            for i in range(d):
                R.append(mpk['e_gh'] ** (1/(X[i]+time)))
                y2 *= R[i] ** X[i]
            r = mpk['g'] ** (1/(PRFkey+time))
            C = ID * (pair(r, mpk['pp']))
            C1 = pair(r, pk['pk'][N])
            (proof1) = PoK.prover1(mpk['g'],A,PRFkey,mpk['vk']) #Proof of SPS
            (proof2) = PoK.prover4(y2,X,R) # Proof of Aggeragetd collatorals
            (proof3) = PoK.prover3(r,C1**PRFkey,PRFkey,pk['pk'][N]) #Proof of ciphertext C1
            (proof4) = PoK.prover2(C,mpk['e_gh'],((C/ID)**PRFkey)*(mpk['e_gh']**(-time*IDsk)),PRFkey,(-time*IDsk)) #Proof of ciphertext C0
            ct = { 'C': C, 'C1': C1, 'R':R }
            return (ct, proof1, proof2, proof3, proof4)
        else:
            return (print("You don't have enough money in your account"), None)
    @Input(mpk_t, pk_t, Rand_t, GT, GT, ct_t, proof_t, proof_t, proof_t, proof1_t, int, list, ZR, int)
    @Output(list)
    def Verification(self, mpk, pk, Rand, L1, L2, ct, proof1, proof2, proof3, proof4, d, Ledger, time, N):
        LHS=1
        for i in range(len(ct['R'])):
            LHS *= (mpk['e_gh'] * ct['R'][i] ** (-time)) 
        if pair(Rand['Sprime'], Rand['Rprime']) == proof1['y'] * mpk['e_Xh'] ** d and \
            pair(Rand['Tprime'],Rand['Rprime']) == pair(Rand['Sprime'],mpk['vk']) * mpk['e_gh']**d and \
                LHS==proof2['y'] and \
                    L1 * (ct['C']**(-time)) == proof4['y'] and \
                    L2 * (ct['C1'] ** (-time)) == proof3['y'] and \
                    PoK.verifier3(mpk['g'],proof1['y'],proof1['z'],proof1['t'],mpk['vk']) == 1 and \
                        PoK.verifier5(proof2['y'],proof2['z'],proof2['t'],ct['R']) == 1 and \
                            PoK.verifier4(proof3['y'],proof3['z'],proof3['t'],ct['C1'],pk['pk'][N]) == 1 and \
                                PoK.verifier2(ct['C'],mpk['e_gh'],proof4['y'],proof4['z1'],proof4['z2'],proof4['t'])==0 and \
                                ct['R'] not in Ledger:
                Ledger.append(ct['R'])
                return Ledger
        else:
            return Ledger

    @Input(mpk_t, ct_t, int, ct_t, int)
    @Output(GT)
    def Decryption(self, mpk, ct1, M1, ct2, M2): 
        Coeff = SSS.recoverCoefficients([group.init(ZR, M1+1),group.init(ZR, M2+1)])
        return ct2['C'] / ((ct1['C1']**Coeff[M1+1])*(ct2['C1']**Coeff[M2+1]))
