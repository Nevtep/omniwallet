// sjcl uses the console which isnt available in a web worker
console = { 
  log: function() {}
}

// jsrsasign and forge exepect that the global object is window.
window = this;

importScripts(
    "/bower_components/jsrsasign/jsrsasign-latest-all-min.js",
    "/bower_components/forge/js/forge.min.js",
    "/bower_components/sjcl/sjcl.js",
    "/js/cryptUtil.js"
);

onmessage = function(oEvent) {
  var jobDesc = oEvent.data;
  var result = null;
  switch (jobDesc.name) {
   	case "generateNonceForDifficulty":
   	  result = CryptUtil.generateNonceForDifficulty(jobDesc.challengeString);
   	  break;
   	case "generateAsymmetricPair":
   	  result = CryptUtil.generateAsymmetricPair();
   	  break;
   	case "generateSymmetricKey":
   	  result = CryptUtil.generateSymmetricKey(jobDesc.password, jobDesc.hexSalt);
   	  break;
   	case "encryptObject":
   	  result = CryptUtil.encryptObject(jobDesc.o, jobDesc.key);
   	  break;
   	case "decryptObject":
   	  result = CryptUtil.decryptObject(jobDesc.string, jobDesc.key);
   	  break;
   	case "createSignedObject":
   	  result = CryptUtil.createSignedObject(jobDesc.data, jobDesc.privKey);
   	  break;
   	default:
   	  break;
  }
  
  postMessage(result);
}
