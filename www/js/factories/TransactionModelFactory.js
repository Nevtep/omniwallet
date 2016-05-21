angular.module("omniFactories")
	.factory("Transaction",["TESTNET","SATOSHI_UNIT",function TransactionModelFactory(TESTNET,SATOSHI_UNIT){
		var TransactionModel = function(txType,fromAddress,txData){
			var self = this;

			self.configure = function(type,address,data){
				self.type = type;

				if(address.privkey){
					self.privKey = new Bitcoin.ECKey.decodeEncryptedFormat(address.privkey, address.hash); // Using address as temporary password
                    self.pubKey = self.privKey.getPubKeyHex();

					self.offline = false;
				}else if(address.pubkey){
					self.pubKey = address.pubkey.toUpperCase();

					self.offline = true;
				}else
					throw "Transaction needs an Address with private or public key"; // Throw an error?

				self.address = address;
				self.data = data;

                self.data['pubkey'] = self.pubKey;
                self.data['transaction_from'] = self.address.hash;
                self.data['testnet'] = TESTNET || false;

                self.totalCost = new Big(); // TODO: calculate protocol cost
			}

			self.configure(txType,fromAddress,txData)
		}

		return TransactionModel;
	}])