import urlparse
import os, sys, re, random, pybitcointools, bitcoinrpc, math
from decimal import Decimal
from flask import Flask, request, jsonify, abort, json, make_response
from msc_apps import *
from blockchain_utils import *
import config

class OmniTransaction:
    confirm_target=6
    HEXSPACE_SECOND='21'
    mainnet_exodus_address='1EXoDusjGwvnjZUyKkxZ4UHEf77z6A5S4P'
    testnet_exodus_address='mpexoDuSkGGqvqrkrjiFng38QPkJQVFyqv'

    def __init__(self,tx_type,form):
        self.conn = getRPCconn()
        self.testnet = False
        self.magicbyte = 0
        self.exodus_address=self.mainnet_exodus_address

        if 'testnet' in form and ( form['testnet'] in ['true', 'True'] ):
            self.testnet =True
            self.magicbyte = 111
            self.exodus_address=self.testnet_exodus_address

        try:
          if config.D_PUBKEY and ( 'donate' in form ) and ( form['donate'] in ['true', 'True'] ):
            print "We're Donating to pubkey for: "+pybitcointools.pubkey_to_address(config.D_PUBKEY)
            self.pubkey = config.D_PUBKEY
          else:
            print "not donating"
            self.pubkey = form['pubkey']
        except NameError, e:
          print e
          self.pubkey = form['pubkey']
        self.fee = estimateFee(self.confirm_target)['result']
        self.rawdata = form
        self.tx_type = tx_type

    def get_unsigned(self):
        # get payload for class C tx
        #payload = self.__generate_payload(self.tx_type, self.rawdata)
        #if payload > 80 bytes:
        #   return self.__generate_class_C_tx()

        return self.__generate_class_B_tx()
    def __generate_class_B_tx(self):
        self.txdata = self.__prepare_txdata(self.tx_type, self.rawdata)
        txbytes = self.__prepare_txbytes(self.txdata)
        packets = self.__construct_packets( txbytes[0], txbytes[1], self.rawdata['transaction_from'] )
        if self.tx_type in [20, 50,51,54,56]:
            try:
                unsignedhex = self.__build_transaction( self.fee, self.pubkey, packets[0], packets[1], packets[2], self.rawdata['transaction_from'])
                #DEBUG print txbytes, packets, unsignedhex
                return { 'status':200, 'unsignedhex': unsignedhex[0] , 'sourceScript': unsignedhex[1] }
            except Exception as e:
                return { 'status': 502, 'data': 'Unspecified error '+str(e)}
        elif self.tx_type == 0:
            try:
                unsignedhex= self.__build_transaction( self.fee, self.pubkey, packets[0], packets[1], packets[2], self.rawdata['transaction_from'], self.rawdata['transaction_to'])
                #DEBUG print tx0bytes, packets, unsignedhex
                return { 'status': 200, 'unsignedhex': unsignedhex[0] , 'sourceScript': unsignedhex[1] }
            except Exception as e:
                return { 'status': 502, 'data': 'Unspecified error '+str(e)}
        elif self.tx_type == 55:
            try:
                if 'transaction_to' in self.rawdata:
                  unsignedhex= self.__build_transaction( self.fee, self.pubkey, packets[0], packets[1], packets[2], self.rawdata['transaction_from'], self.rawdata['transaction_to'])
                else:
                  unsignedhex= self.__build_transaction( self.fee, self.pubkey, packets[0], packets[1], packets[2], self.rawdata['transaction_from'])

                #DEBUG print tx0bytes, packets, unsignedhex
                return { 'status': 200, 'unsignedhex': unsignedhex[0] , 'sourceScript': unsignedhex[1] }
            except Exception as e:
                return { 'status': 502, 'data': 'Unspecified error '+str(e)} 
    # Class B helper funcs
    def __prepare_txdata(self, txtype,form):
        #print "txtype"
        #print txtype
        #print "form"
        #print form
        txdata=[]

        txdata.append(int(form['transaction_version']))
        txdata.append(int(txtype))
        
        #if txtype == 50 or txtype == 51:
        if txtype == 20:
            txdata.append(int(form['currency_identifier']))
            txdata.append(int(form['amount_for_sale']))
            txdata.append(int(form['amount_desired']))
            txdata.append(int(form['blocks']))
            txdata.append(int(form['min_buyer_fee']))
        #elif txtype == 22:
        elif txtype in [50,51,54]:
            txdata.append(int(form['ecosystem']))
            txdata.append(int(form['property_type']))
            txdata.append(int(form['previous_property_id']))

            property_category=form['property_category']
            property_category+='\0' if property_category[-1] != '\0' else ''
            txdata.append(property_category)

            property_subcategory=form['property_subcategory']
            property_subcategory+='\0' if property_subcategory[-1] != '\0' else ''
            txdata.append(property_subcategory)

            property_name=form['property_name']
            property_name+='\0' if property_name[-1] != '\0' else ''
            txdata.append(property_name)

            property_url=form['property_url']
            property_url+='\0' if property_url[-1] != '\0' else ''
            txdata.append(property_url)

            property_data=form['property_data']
            property_data+='\0' if property_data[-1] != '\0' else ''
            txdata.append(property_data)

            if txtype == 50:
                txdata.append(int(form['number_properties']))
            elif txtype == 51:
                txdata.append(int(form['number_properties']))
                txdata.append(int(form['currency_identifier_desired']))
                txdata.append(int(form['deadline']))
                txdata.append(int(math.ceil(float(form['earlybird_bonus']))))
                txdata.append(int(math.ceil(float(form['percentage_for_issuer']))))
            
            return txdata
        elif txtype ==0:
            txdata.append(int(form['currency_identifier']))
            txdata.append(int(form['amount_to_transfer']))
            
            return txdata
        elif txtype in [55,56]:
            txdata.append(int(form['currency_identifier']))
            txdata.append(int(form['number_properties']))
            if 'memo' in form:
              memo=form['memo']
              memo+='\0' if memo[-1] != '\0' else ''
              txdata.append(memo)

            return txdata

        return [] #other txes are unimplemented
    def __prep_bytes(self, letter):
        #print "prep bytes"
        #print letter
        hex_bytes = hex(ord(letter))[2:]
        if len(hex_bytes) % 2 == 1:
            hex_bytes = hex_bytes[:len(hex_bytes)-1]
        if len(hex_bytes) > 255:
            hex_bytes = hex_bytes[255:]
        
        return hex_bytes

    def __prepare_txbytes(self, txdata):
        #print "prepare txbytes"
        #print txdata
        #calculate bytes
        tx_ver_bytes = hex(txdata[0])[2:].rstrip('L').rjust(4,"0") # 2 bytes
        tx_type_bytes = hex(txdata[1])[2:].rstrip('L').rjust(4,"0")   # 2 bytes
        if txdata[1] in [50,51,54]:
            eco_bytes = hex(txdata[2])[2:].rstrip('L').rjust(2,"0")              # 1 byte
            prop_type_bytes = hex(txdata[3])[2:].rstrip('L').rjust(4,"0")    # 2 bytes
            prev_prop_id_bytes = hex(txdata[4])[2:].rstrip('L').rjust(8,"0")  # 4 bytes
            prop_cat_bytes = ''                                      # var bytes
            prop_subcat_bytes = ''                                   # var bytes
            prop_name_bytes = ''                                     # var bytes
            prop_url_bytes = ''                                      # var bytes
            prop_data_bytes = ''                                     # var bytes

            if txdata[1] == 50:
                num_prop_bytes = hex(txdata[10])[2:].rstrip('L').rjust(16,"0")        # 8 bytes
            elif txdata[1] == 51:
                num_prop_bytes = hex(txdata[10])[2:].rstrip('L').rjust(16,"0")# 8 bytes
                curr_ident_des_bytes = hex(txdata[11])[2:].rstrip('L').rjust(8,"0")      # 4 bytes
                deadline_bytes = hex(txdata[12])[2:].rstrip('L').rjust(16,"0")         # 8 bytes
                earlybird_bytes = hex(txdata[13])[2:].rstrip('L').rjust(2,"0")        # 1 byte
                percent_issuer_bytes = hex(txdata[14])[2:].rstrip('L').rjust(2,"0") # 1 byte
                
            for let in txdata[5]:
                prop_cat_bytes += self.__prep_bytes(let)
            prop_cat_bytes += '00'
        
            for let in txdata[6]:
                prop_subcat_bytes += self.__prep_bytes(let) 
            prop_subcat_bytes += '00'
        
            for let in txdata[7]:
                prop_name_bytes += self.__prep_bytes(let)
            prop_name_bytes += '00'
        
            for let in txdata[8]:
                prop_url_bytes += self.__prep_bytes(let)
            prop_url_bytes += '00'
        
            for let in txdata[9]:
                prop_data_bytes += self.__prep_bytes(let)
            prop_data_bytes += '00'
        
            if txdata[1] == 50:
                total_bytes = (len(tx_ver_bytes) + 
                            len(tx_type_bytes) + 
                            len(eco_bytes) + 
                            len(prop_type_bytes) + 
                            len(prev_prop_id_bytes) + 
                            len(num_prop_bytes) + 
                            len(prop_cat_bytes) + 
                            len(prop_subcat_bytes) + 
                            len(prop_name_bytes) + 
                            len(prop_url_bytes) + 
                            len(prop_data_bytes))/2
        
                byte_stream = (tx_ver_bytes + 
                            tx_type_bytes + 
                            eco_bytes + 
                            prop_type_bytes + 
                            prev_prop_id_bytes + 
                            prop_cat_bytes + 
                            prop_subcat_bytes + 
                            prop_name_bytes + 
                            prop_url_bytes + 
                            prop_data_bytes + 
                            num_prop_bytes)
                
                #DEBUG print [tx_ver_bytes,tx_type_bytes,eco_bytes,prop_type_bytes,prev_prop_id_bytes,num_prop_bytes,prop_cat_bytes,prop_subcat_bytes,prop_name_bytes,prop_url_bytes,prop_data_bytes]
                
                #DEBUG print [len(tx_ver_bytes)/2,len(tx_type_bytes)/2,len(eco_bytes)/2,len(prop_type_bytes)/2,len(prev_prop_id_bytes)/2,len(num_prop_bytes)/2,len(prop_cat_bytes)/2,len(prop_subcat_bytes)/2,len(prop_name_bytes)/2,len(prop_url_bytes)/2,len(prop_data_bytes)/2]
        
            elif txdata[1] == 51:
                total_bytes = (len(tx_ver_bytes) + 
                            len(tx_type_bytes) + 
                            len(eco_bytes) + 
                            len(prop_type_bytes) + 
                            len(prev_prop_id_bytes) + 
                            len(num_prop_bytes) +
                            len(curr_ident_des_bytes) +
                            len(deadline_bytes) +
                            len(earlybird_bytes) +
                            len(percent_issuer_bytes) +
                            len(prop_cat_bytes) + 
                            len(prop_subcat_bytes) + 
                            len(prop_name_bytes) + 
                            len(prop_url_bytes) + 
                            len(prop_data_bytes))/2
        
                byte_stream = (tx_ver_bytes + 
                            tx_type_bytes + 
                            eco_bytes + 
                            prop_type_bytes + 
                            prev_prop_id_bytes + 
                            prop_cat_bytes + 
                            prop_subcat_bytes + 
                            prop_name_bytes + 
                            prop_url_bytes + 
                            prop_data_bytes +
                            curr_ident_des_bytes +
                            num_prop_bytes +
                            deadline_bytes +
                            earlybird_bytes +
                            percent_issuer_bytes)
        
                #DEBUG print [tx_ver_bytes,tx_type_bytes,eco_bytes,prop_type_bytes,prev_prop_id_bytes,num_prop_bytes,prop_cat_bytes,prop_subcat_bytes,prop_name_bytes,prop_url_bytes,prop_data_bytes]
        
                #DEBUG print [len(tx_ver_bytes)/2,len(tx_type_bytes)/2,len(eco_bytes)/2,len(prop_type_bytes)/2,len(prev_prop_id_bytes)/2,len(num_prop_bytes)/2,len(prop_cat_bytes)/2,len(prop_subcat_bytes)/2,len(prop_name_bytes)/2,len(prop_url_bytes)/2,len(prop_data_bytes)/2]
        if txdata[1] == 54:
                total_bytes = (len(tx_ver_bytes) +
                            len(tx_type_bytes) +
                            len(eco_bytes) +
                            len(prop_type_bytes) +
                            len(prev_prop_id_bytes) +
                            len(prop_cat_bytes) +
                            len(prop_subcat_bytes) +
                            len(prop_name_bytes) +
                            len(prop_url_bytes) +
                            len(prop_data_bytes))/2

                byte_stream = (tx_ver_bytes +
                            tx_type_bytes +
                            eco_bytes +
                            prop_type_bytes +
                            prev_prop_id_bytes +
                            prop_cat_bytes +
                            prop_subcat_bytes +
                            prop_name_bytes +
                            prop_url_bytes +
                            prop_data_bytes)

        elif txdata[1] in [55,56]:
            currency_id_bytes = hex(txdata[2])[2:].rstrip('L').rjust(8,"0")  # 4 bytes
            amount_bytes = hex(txdata[3])[2:].rstrip('L').rjust(16,"0")  # 8 bytes
            memo_bytes = ''

            for let in txdata[4]:
                memo_bytes += self.__prep_bytes(let)
            memo_bytes += '00'

            total_bytes = (len(tx_ver_bytes) +
                            len(tx_type_bytes) +
                            len(currency_id_bytes) +
                            len(amount_bytes) +
                            len(memo_bytes))/2

            byte_stream = (tx_ver_bytes +
                        tx_type_bytes +
                        currency_id_bytes +
                        amount_bytes +
                        memo_bytes)


        elif txdata[1] == 0:
            currency_id_bytes = hex(txdata[2])[2:].rstrip('L').rjust(8,"0")  # 4 bytes
            amount_bytes = hex(txdata[3])[2:].rstrip('L').rjust(16,"0")  # 8 bytes
            
            total_bytes = (len(tx_ver_bytes) + 
                            len(tx_type_bytes) + 
                            len(currency_id_bytes) + 
                            len(amount_bytes))/2
        
            byte_stream = (tx_ver_bytes + 
                        tx_type_bytes + 
                        currency_id_bytes + 
                        amount_bytes)
        elif txdata[1] == 20:
            currency_id_bytes = hex(txdata[2])[2:].rstrip('L').rjust(8,"0")  # 4 bytes
            amount_for_sale_bytes = hex(txdata[3])[2:].rstrip('L').rjust(16,"0")  # 8 bytes
            amount_desired_bytes = hex(txdata[4])[2:].rstrip('L').rjust(16,"0")  # 8 bytes
            blocks = hex(txdata[5])[2:].rstrip('L').rjust(2,"0")        # 1 byte
            min_buyer_fee = hex(txdata[6])[2:].rstrip('L').rjust(16,"0") # 8 bytes

            total_bytes = (len(tx_ver_bytes) + 
                            len(tx_type_bytes) + 
                            len(currency_id_bytes) + 
                            len(amount_for_sale_bytes) + 
                            len(amount_desired_bytes) + 
                            len(blocks) + 
                            len(min_buyer_fee))/2
        
            byte_stream = (tx_ver_bytes + 
                        tx_type_bytes + 
                        currency_id_bytes + 
                        amount_for_sale_bytes + 
                        amount_desired_bytes + 
                        blocks + 
                        min_buyer_fee)  

        return [byte_stream, total_bytes]

    def __construct_packets(self, byte_stream, total_bytes, from_address):
        #print "construct packets byte_stream, total_bytes, from_address"
        #print byte_stream, total_bytes, from_address

        import math
        total_packets = int(math.ceil(float(total_bytes)/30)) #get # of packets
        
        total_outs = int(math.ceil(float(total_packets)/2)) #get # of outs
        
        #construct packets
        packets = []
        index = 0
        for i in range(total_packets):
            # 2 multisig data addrs per out, 60 bytes per, 2 characters per byte so 60 characters per pass
            parsed_data = byte_stream[index:index+60].ljust(60,"0")
            cleartext_packet =  (hex(i+1)[2:].rjust(2,"0") + parsed_data.ljust(60,"0"))
        
            index = index+60
            packets.append(cleartext_packet)
            #DEBUG print ['pax',cleartext_packet, parsed_data, total_packets, i]
        
        
        obfuscation_packets = [hashlib.sha256(from_address).hexdigest().upper()]  #add first sha of sender to packet list
        for i in range(total_packets-1): #do rest for seqnums
            obfuscation_packets.append(hashlib.sha256(obfuscation_packets[i]).hexdigest().upper())
        
        #DEBUG print [packets,obfuscation_packets, len(obfuscation_packets[0]), len(obfuscation_packets[1]), len(packets[0])]
        
        #obfuscate and prepare multisig outs
        pair_packets = []
        for i in range(total_packets):
            obfuscation_packet = obfuscation_packets[i]
            pair_packets.append((packets[i], obfuscation_packet[:-2]))
        
        #encode the plaintext packets
        obfuscated_packets = []
        for pair in pair_packets:
            plaintext = pair[0].upper()
            shaaddress = pair[1] 
            #DEBUG print ['packets', plaintext, shaaddress, len(plaintext), len(shaaddress)]
            datapacket = ''
            for i in range(len(plaintext)):
                if plaintext[i] == '0':
                    datapacket = datapacket + shaaddress[i]
                else:
                    bin_plain = int('0x' + plaintext[i], 16)
                    bin_sha = int('0x' + shaaddress[i], 16)
                    #DEBUG print ['texts, plain & addr', plaintext[i], shaaddress[i],'bins, plain & addr', bin_plain, bin_sha ]
                    xored = hex(bin_plain ^ bin_sha)[2:].upper()
                    datapacket = datapacket + xored
            obfuscated_packets.append(( datapacket, shaaddress))
        
        #### Test that the obfuscated packets produce the same output as the plaintext packet inputs ####
        
        #decode the obfuscated packet
        plaintext_packets = []
        for pair in obfuscated_packets:
            obpacket = pair[0].upper()
            shaaddress = pair[1]
            #DEBUG print [obpacket, len(obpacket), shaaddress, len(shaaddress)]
            datapacket = ''
            for i in range(len(obpacket)):
                if obpacket[i] == shaaddress[i]:
                    datapacket = datapacket + '0'
                else:
                    bin_ob = int('0x' + obpacket[i], 16)
                    bin_sha = int('0x' + shaaddress[i], 16)
                    xored = hex(bin_ob ^ bin_sha)[2:].upper()
                    datapacket = datapacket + xored
            plaintext_packets.append(datapacket)
        
        #check the packet is formed correctly by comparing it to the input
        final_packets = []
        for i in range(len(plaintext_packets)):
            orig = packets[i]
            if orig.upper() != plaintext_packets[i]:
                print ['packet did not come out right', orig, plaintext_packets[i] ]
            else:
                final_packets.append(obfuscated_packets[i][0])
        
        #DEBUG print plaintext_packets, obfuscation_packets,final_packets
        
        #add key identifier and ecdsa byte to new mastercoin data key
        for i in range(len(final_packets)):
            obfuscated = '02' + final_packets[i] + "00" 
            #DEBUG print [obfuscated, len(obfuscated)]
            invalid = True
            while invalid:
                obfuscated_randbyte = obfuscated[:-2] + hex(random.randint(0,255))[2:].rjust(2,"0").upper()
                #set the last byte to something random in case we generated an invalid pubkey
                potential_data_address = pybitcointools.pubkey_to_address(obfuscated_randbyte, self.magicbyte)
                
                if bool(self.conn.validateaddress(potential_data_address).isvalid):
                    final_packets[i] = obfuscated_randbyte
                    invalid = False
            #make sure the public key is valid using pybitcointools, if not, regenerate 
            #the last byte of the key and try again
        
        #DEBUG print final_packets 
        return [final_packets,total_packets,total_outs]
        
    def __build_transaction(self, miner_fee_btc, pubkey,final_packets, total_packets, total_outs, from_address, to_address=None):
        print "build_transaction", miner_fee_btc, pubkey,final_packets, total_packets, total_outs, from_address, to_address
        print 'pubkey', pubkey, len(pubkey) 
        if len(pubkey) < 100:
          print "Compressed Key, using hexspace 21"
          HEXSPACE_FIRST='21'
        else:
          HEXSPACE_FIRST='41'

        #calculate fees
        miner_fee = Decimal(miner_fee_btc)
        if to_address==None or to_address==from_address:
             #change goes to sender/receiver
            print "Single extra fee calculation"  
            fee_total = Decimal(miner_fee) + Decimal(0.00005757*total_packets+0.00005757*total_outs) + Decimal(0.00005757)  #exodus output is last
        else:
            #need 1 extra output for exodus and 1 for receiver.
            print "Double extra fee calculation"
            fee_total = Decimal(miner_fee) + Decimal(0.00005757*total_packets+0.00005757*total_outs) + Decimal(2*0.00005757)  #exodus output is last
        fee_total_satoshi = int( round( fee_total * Decimal(1e8) ) )

        #------------------------------------------- New utxo calls
        print "Calling bc_getutxo with ", from_address, fee_total_satoshi
        dirty_txes = bc_getutxo( from_address, fee_total_satoshi )
        print "received", dirty_txes

        if (dirty_txes['error'][:3]=='Con'):
            raise Exception({ "status": "NOT OK", "error": "Couldn't get list of unspent tx's. Response Code: " + dirty_txes['code']  })

        if (dirty_txes['error'][:3]=='Low'):
            raise Exception({ "status": "NOT OK", "error": "Not enough funds, try again. Needed: " + str(fee_total) + " but Have: " + dirty_txes['avail']  })

        total_amount = dirty_txes['avail']
        unspent_tx = dirty_txes['utxos']

        change = total_amount - fee_total_satoshi

        #DEBUG 
        print [ "Debugging...", dirty_txes,"miner fee sats: ", miner_fee_btc,"miner fee: ", miner_fee, "change: ",change,"total_amt: ", total_amount,"fee tot sat: ", fee_total_satoshi,"utxo ",  unspent_tx,"total pax ", total_packets, "total outs ",total_outs,"to ", to_address ]

        #source script is needed to sign on the client credit grazcoin
        hash160=bc_address_to_hash_160(from_address).encode('hex_codec')
        prevout_script='OP_DUP OP_HASH160 ' + hash160 + ' OP_EQUALVERIFY OP_CHECKSIG'

        validnextinputs = []   #get valid redeemable inputs
        for unspent in unspent_tx:
            #retrieve raw transaction to spend it
            prev_tx = self.conn.getrawtransaction(unspent[0])

            for output in prev_tx.vout:
                if 'reqSigs' in output['scriptPubKey'] and output['scriptPubKey']['reqSigs'] == 1 and output['scriptPubKey']['type'] != 'multisig':
                    for address in output['scriptPubKey']['addresses']:
                        if address == from_address and int(output['n']) == int(unspent[1]):
                            validnextinputs.append({ "txid": prev_tx.txid, "vout": output['n']})
                            break


        validnextoutputs = { self.exodus_address: 0.00005757 }
        if to_address != None:
            validnextoutputs[to_address]=0.00005757 #Add for simple send
        
        if change >= 5757: # send anything above dust to yourself
            validnextoutputs[ from_address ] = float( Decimal(change)/Decimal(1e8) )
        
        unsigned_raw_tx = self.conn.createrawtransaction(validnextinputs, validnextoutputs)
        
        #DEBUG print change,unsigned_raw_tx

        json_tx =  self.conn.decoderawtransaction(unsigned_raw_tx)
        
        #append  data structure
        ordered_packets = []
        for i in range(total_outs):
            ordered_packets.append([])
        
        #append actual packet
        index = 0
        for i in range(total_outs):
            while len(ordered_packets[i]) < 2 and index != len(final_packets):
                ordered_packets[i].append(final_packets[index])
                index = index + 1
        #DEBUG print ordered_packets
        
        for i in range(total_outs):
            hex_string = "51" + HEXSPACE_FIRST + pubkey
            asm_string = "1 " + pubkey
            addresses = [ pybitcointools.pubkey_to_address(pubkey, self.magicbyte)]
            n_count = len(validnextoutputs)+i
            total_sig_count = 1
            #DEBUG print [i,'added string', ordered_packets[i]]
            for packet in ordered_packets[i]:
                hex_string = hex_string + self.HEXSPACE_SECOND + packet.lower() 
                asm_string = asm_string + " " + packet.lower()
                addresses.append(pybitcointools.pubkey_to_address(packet, self.magicbyte))
                total_sig_count = total_sig_count + 1
            hex_string = hex_string + "5" + str(total_sig_count) + "ae"
            asm_string = asm_string + " " + str(total_sig_count) + " " + "OP_CHECKMULTISIG"
            #DEBUG 
            print ["hex string, asm string, addrs, total_sigs, ", hex_string, asm_string, addresses,total_sig_count]
            #add multisig output to json object
            json_tx['vout'].append(
                { 
                    "scriptPubKey": 
                    { 
                        "hex": hex_string, 
                        "asm": asm_string, 
                        "reqSigs": 1, 
                        "type": "multisig", 
                        "addresses": addresses 
                    }, 
                    "value": 0.00005757*len(addresses), 
                    "n": n_count
                })
        
        #DEBUG import pprint    
        #DEBUG print pprint.pprint(json_tx)
        
        #construct byte arrays for transaction 
        #assert to verify byte lengths are OK
        version = ['01', '00', '00', '00' ]
        assert len(version) == 4
        
        num_inputs = [str(hex(len(json_tx['vin']))[2:]).rjust(2,"0")]
        assert len(num_inputs) == 1
        
        num_outputs = [str(hex(len(json_tx['vout']))[2:]).rjust(2,"0")]
        assert len(num_outputs) == 1
        
        sequence = ['FF', 'FF', 'FF', 'FF']
        assert len(sequence) == 4
        
        blocklocktime = ['00', '00', '00', '00']
        assert len(blocklocktime) == 4
        
        #prepare inputs data for byte packing
        inputsdata = []
        for _input in json_tx['vin']:
            prior_input_txhash = _input['txid'].upper()  
            ihex = str(hex(_input['vout'])[2:]).rjust(2,"0")
            lhex = len(ihex)
            if lhex in [1,2]:
                prior_input_index = ihex.ljust(8,"0")
            elif lhex in [3,4]: 
                prior_input_index = ihex[-2:].rjust(2,"0")+ihex[:-2].rjust(2,"0").ljust(6,"0")
            elif lhex in [5,6]: 
                prior_input_index = ihex[-2:].rjust(2,"0")+ihex[-4:-2].rjust(2,"0")+ihex[:-4].rjust(2,"0").ljust(4,"0")
            elif lhex in [7,8]: 
                prior_input_index = ihex[-2:].rjust(2,"0")+ihex[-4:-2].rjust(2,"0")+ihex[-6:-4].rjust(2,"0")+ihex[:-6].rjust(2,"0").ljust(2,"0")
            input_raw_signature = _input['scriptSig']['hex']
            
            prior_txhash_bytes =  [prior_input_txhash[ start: start + 2 ] for start in range(0, len(prior_input_txhash), 2)][::-1]
            assert len(prior_txhash_bytes) == 32
        
            prior_txindex_bytes = [prior_input_index[ start: start + 2 ] for start in range(0, len(prior_input_index), 2)]
            assert len(prior_txindex_bytes) == 4
        
            len_scriptsig = ['%02x' % len(''.join([]).decode('hex').lower())] 
            assert len(len_scriptsig) == 1
            
            inputsdata.append([prior_txhash_bytes, prior_txindex_bytes, len_scriptsig])
        
        #prepare outputs for byte packing
        output_hex = []
        for output in json_tx['vout']:
            value_hex = hex(int(float(output['value'])*1e8))[2:]
            value_hex = value_hex.rjust(16,"0")
            value_bytes =  [value_hex[ start: start + 2 ].upper() for start in range(0, len(value_hex), 2)][::-1]
            assert len(value_bytes) == 8
            
           # print output
            scriptpubkey_hex = output['scriptPubKey']['hex']
            scriptpubkey_bytes = [scriptpubkey_hex[start:start + 2].upper() for start in range(0, len(scriptpubkey_hex), 2)]
            len_scriptpubkey = ['%02x' % len(''.join(scriptpubkey_bytes).decode('hex').lower())]
            #assert len(scriptpubkey_bytes) == 25 or len(scriptpubkey_bytes) == 71
        
            output_hex.append([value_bytes, len_scriptpubkey, scriptpubkey_bytes] )
        
        #join parts into final byte array
        hex_transaction = version + num_inputs
        
        for _input in inputsdata:
            hex_transaction += (_input[0] + _input[1] + _input[2] + sequence)
        
        hex_transaction += num_outputs
        
        for output in output_hex:
            hex_transaction = hex_transaction + (output[0] + output[1] + output[2]) 
        
        hex_transaction = hex_transaction + blocklocktime
        
        #verify that transaction is valid
        try:
          decoded_tx = self.conn.decoderawtransaction(''.join(hex_transaction).lower());
        except Exception as e:
          raise Exception({ "status": "NOT OK", "error": str(e)+" : Please contact an developer"  })

        if 'txid' not in decoded_tx:
            raise Exception({ "status": "NOT OK", "error": "Network byte mismatch: Please try again"  })

        #DEBUG 
        print 'final hex ', ''.join(hex_transaction).lower()
        #DEBUG print pprint.pprint(self.conn.decoderawtransaction(''.join(hex_transaction).lower()))

        unsigned_hex=''.join(hex_transaction).lower()

        return [unsigned_hex, prevout_script]