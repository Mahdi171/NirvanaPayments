from charm.toolbox.pairinggroup import PairingGroup,ZR,G1,G2,GT,pair
from charm.toolbox.secretutil import SecretUtil
from charm.toolbox.ABEnc import Input, Output
from secretshare import SecretShare
from charm.core.engine.util import serializeDict,objectToBytes, bytesToObject
import random
import time
import zmq
from datetime import datetime
from openpyxl import load_workbook
from openpyxl import Workbook
from PoK import PoK

mpk_t = { 'g':G1, 'h':G2, 'pp': G2, 'e_gh':GT, 'e_Xh':GT, 'vk':G2 , 'X': G1 }
pk_t = { 'pk':G2, 'Merlist':str }
Col_t = { 'PRFkey': ZR, 'key':G1, 'R':G2, 'S':G1, 'T':G1, 'W':G1 }
Rand_t = {'Rprime':G2, 'Sprime':G1, 'Tprime':G1, 'Wprime':G1}
ct_t = { 'C':GT, 'C1':GT, 'R':GT}
proof1_t = {'p1z': ZR, 'p1t': GT, 'p1y': GT}
proof4_t = {'p4z': ZR, 'p4t': GT, 'p4y': GT}
proof3_t = {'p3z': ZR, 'p3t': GT, 'p3y': GT}
proof2_t = {'p2z1': ZR, 'p2z2': ZR, 'p2t': GT, 'p2y': GT}



class Customer():

    def __init__(self):
        global Mer, groupObj
        groupObj = PairingGroup('BN254')
        self.PoK = PoK(groupObj)
        self.SSS = SecretShare(groupObj)
        Mer = ['Apple','Ebay','Tesco','Amazon','Tesla','Colruyt','BMW','hp','Albert','IKEA'] 
        
    #Requesting public parameters
    @Output(mpk_t)
    def request_pp(self):
        self.context = zmq.Context()
        print("Connecting to NirvanaTTP, requesting parameters...")
        socket_pull = self.context.socket(zmq.PULL)
        socket_pull.connect("tcp://10.0.2.15:5556")
        mpk = socket_pull.recv()
        mpk = bytesToObject(mpk, groupObj)
        #print(mpk)
        socket_pull.close()
        return mpk

    #requesting collateral proof from Nirvana    
    @Output(mpk_t, Col_t)
    def request_col(self): 
        self.context = zmq.Context()
        print("Connecting to NirvanaTTP, requesting collateral proof...")
        socket = self.context.socket(zmq.REQ)
        socket.connect("tcp://localhost:5551")   
        for request in range(1):
            print(f"Sending request {request} ...")
            socket.send_string('15')

            message_colla = socket.recv()
            print("Received collateral proofs..")
            #message_col = message_col.decode('utf-8')
            message_colla = bytesToObject(message_colla, groupObj)
            #print(f"Received collateral [ {message_col} ]")
        socket.close()
        
        return message_colla

    #Generating the payment guarantee for requesting merchant..
    @Input(mpk_t, Col_t, ZR, list, GT, G2, int, GT, ZR,ZR, Rand_t)
    @Output(mpk_t, Rand_t, ct_t,proof1_t, proof4_t, proof3_t, proof2_t, ZR)
    def spend_col(self,mpk, Col, PRFkey, X, A, pk, d, ID, IDsk,time, Rand):
        R=[]; y2=1
        if len(Col['PRFkey']) >= d:
            for i in range(d):
                R.append(mpk['e_gh'] ** (1/(X[i]+time)))
                y2 *= R[i] ** X[i]
            r = mpk['g'] ** (1/(PRFkey+time))
            C = ID * (pair(r, mpk['pp']))
            C1 = pair(r, pk)
            u = mpk['e_gh'] ** (PRFkey * IDsk)
            (proof1) = self.PoK.prover1(mpk['g'],A,PRFkey,mpk['vk']) #Proof of SPS
            (proof2) = self.PoK.prover4(y2,X,R) # Proof of Aggeragetd collatorals
            (proof3) = self.PoK.prover3(r,C1**PRFkey,PRFkey,pk) #Proof of ciphertext C1
            (proof4) = self.PoK.prover2(C,mpk['e_gh'],((C/ID)**PRFkey)*(mpk['e_gh']**(-time*IDsk)),PRFkey,(-time*IDsk)) #Proof of ciphertext C0
            ct = { 'C': C, 'C1': C1, 'R':R, 'u':u }
            spend_proof = (mpk, Rand, ct, proof1, proof2, proof3, proof4, time)
            return spend_proof
            
        #socket_receiveProofReq.close()


#main    
def start_bench(group):
    group.InitBenchmark()
    group.StartBenchmark(["RealTime"])

def end_bench(group):
    group.EndBenchmark()
    benchmarks = group.GetGeneralBenchmarks()
    real_time = benchmarks['RealTime']
    return real_time

c = Customer()
#c.request_pp()
message_colla = (c.request_col())
mpk = message_colla[0]
Col = message_colla[1]
context = zmq.Context()
socket_receiveProofReq = context.socket(zmq.REP)
socket_receiveProofReq.bind("tcp://*:5550")
IDsk = groupObj.random(ZR); ID= mpk['e_gh']**IDsk
def run_comm_trip(i):   
    result = [i]  
    PPSpending_time = 0; 
    for j in range(10):
        merchant_col_req = socket_receiveProofReq.recv()
        print("Received proof request from merchant..")
        merchant_col_req = bytesToObject(merchant_col_req, groupObj)
        pk_message = merchant_col_req[1]
        time=groupObj.hash(objectToBytes(str(datetime.now()), groupObj),ZR)
        SAgg=1; TAgg=1; PRFkey=0; R=[]; X=[]; y2=1
        d = merchant_col_req[0]
        for i in range(d):
            SAgg *= Col['S'][str(i)]
            TAgg *= Col['T'][str(i)]
            PRFkey += Col['PRFkey'][str(i)]
            X.append(Col['PRFkey'][str(i)])
            A = pair(mpk['g'],mpk['vk']) ** PRFkey
        tprime = groupObj.random(ZR)
        Rprime = Col['R'] ** (1/tprime)
        Sprime = SAgg ** tprime
        Tprime = (TAgg ** (tprime**2))* (Col['W']**(d*tprime*(1-tprime)))
        Wprime = Col['W'] ** (1/tprime)
        Rand = { 'Rprime':Rprime, 'Sprime':Sprime, 'Tprime':Tprime, 'Wprime':Wprime }
        start_bench(groupObj)
        spend_proof = c.spend_col(mpk, Col,PRFkey,X,A, pk_message, d, ID, IDsk, time, Rand)
        PPSpending_time += end_bench(groupObj)
        spend_proof = objectToBytes(spend_proof, groupObj)
        socket_receiveProofReq.send(spend_proof)
        print("Sent payment guarantee to merchant....")
    PPSpending_time = (PPSpending_time*100)
    result.append(PPSpending_time)        
    return result


book=Workbook()
data=book.active    
title = ['d','Spending Time']
data.append(title) 
for i in range(1,11):
    result=run_comm_trip(i)  
    data.append(result)
book.save('Spend_comm_preprocc.xlsx')