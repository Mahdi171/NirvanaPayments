        

def start_bench(group):
    group.InitBenchmark()
    group.StartBenchmark(["RealTime"])

def end_bench(group):
    group.EndBenchmark()
    benchmarks = group.GetGeneralBenchmarks()
    real_time = benchmarks['RealTime']
    return real_time

groupObj = PairingGroup('BN254')
Nir = Nirvana(groupObj)
PoK1 = PoK1(groupObj)
PoK2 = PoK2(groupObj)
PoK3 = PoK3(groupObj)
SSS = SecretShare(groupObj)
Mer = ['Apple'] * 2001

def run_round_trip(n,d,M):
    result=[n,d,M]
    # setup
    
    setup_time = 0
    for i in range(1):
        start_bench(groupObj)
        (mpk, msk) = Nir.Setup()
        setup_time += end_bench(groupObj)
    setup_time = setup_time * 10
    result.append(setup_time)
    public_parameters_size = sum([len(x) for x in serializeDict(mpk, groupObj).values()]) 
    result.append(public_parameters_size)
    # Key Gen
    Merchants = random.sample(Mer, M)
    Key_Gen_time=0
    for i in range(1):
        start_bench(groupObj)
        
        (pk,sk) = Nir.Keygen(mpk, msk, Merchants)
        Key_Gen_time += end_bench(groupObj)
    Key_Gen_time = Key_Gen_time * 10
    public_key_size = sum([len(x) for x in serializeDict(pk, groupObj).values()]) 
    secret_key_size = sum([len(x) for x in serializeDict(sk, groupObj).values()]) 
    secret_key_size = secret_key_size /10
    public_key_size = public_key_size /10
    result.append(Key_Gen_time)
    result.append(public_key_size)
    result.append(secret_key_size)

    # Registeration
    
    Registeration_time=0
    for i in range(1):
        start_bench(groupObj)
        (Col) = Nir.Registeration(mpk, msk, n)
        Registeration_time += end_bench(groupObj)
    Registeration_time = Registeration_time * 10
    Collateral_size = sum([len(x) for x in serializeDict(Col, groupObj).values()]) 
    Collateral_size = Collateral_size /10
    result.append(Registeration_time)
    result.append(Collateral_size)

    # Spending
    
    #N = pk['Merlist'].index('Apple')
    Spending_time = 0; time=groupObj.hash(objectToBytes(str(datetime.now()), group),ZR)
    for i in range(1):
        start_bench(groupObj)
        (ct1, Rand1,proof1,proof2) = Nir.Spending(mpk, Col, pk, time, d, 10)
        Spending_time += end_bench(groupObj)
    Spending_time = Spending_time * 10
    result.append(Spending_time)
    Ciphertext_size = sum([len(x) for x in serializeDict(ct1, groupObj).values()]) + sum([len(x) for x in serializeDict(Rand1, groupObj).values()]) 
    result.append(Ciphertext_size)
    (ct2, Rand2,p1,p2) = Nir.Spending(mpk, Col, pk, time, d, 11)

    # Verification 
    Verification_time = 0
    for i in range(1):
        start_bench(groupObj)
        Ledger=[]
        out = Nir.Verification(mpk,Rand1,ct1,proof1,proof2,d,Ledger,time)
        print(out)
        Verification_time += end_bench(groupObj)
    Verification_time = Verification_time * 10
    result.append(Verification_time) 
    #(out2)= Nir.Verification(mpk,ct2,Rand2)


    # Decryption
    Decryption_time = 0
    for i in range(1):
        start_bench(groupObj)
        (out)= Nir.Decryption(mpk, ct1, 1, ct2, 2)
        Decryption_time += end_bench(groupObj)
    Decryption_time = Decryption_time * 10
    result.append(Decryption_time)

    return result

book=Workbook()
data=book.active
title=["n","d","M","setup_time","public_parameters_size", "Key_Gen_time","public_key_size","secret_key_size","Registeration_time","Collateral_size","Spending_time","Ciphertext_size","Verification_time","Decryption_time"]
data.append(title)
for n in range(2,3):
    data.append(run_round_trip(n,n,50*n))
    print(n)
book.save("Result1.xlsx")

