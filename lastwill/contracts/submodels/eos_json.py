def create_eos_json(
        crowdsale_address, public_key, bytecode, abi, token_address,
        max_supply, token_short_name, is_transferable_at_once, init_data
):
    return {"actions": [
                        {
                        "account": "eosio",
                        "name": "updateauth",
                        "authorization": [{
                            "actor": crowdsale_address,
                            "permission": "active"
                        }],
                         "data": {
                             "account": crowdsale_address,
                             "permission": "active",
                             "parent": "owner",
                             "auth": {
                                 "threshold": 1, "keys":
                                      [{
                                        "key": public_key,
                                        "weight": 1}],
                                        "accounts":
                                            [{"permission": {
                                        "actor": crowdsale_address,
                                        "permission": "eosio.code"},
                                                "weight": 1}],
                                    "waits": []}}},

                        {
                        "account": "eosio",
                        "name": "setcode",
                        "authorization": [{
                            "actor": crowdsale_address,
                            "permission": "active"
                        }],
                        "data": {
                            "account": crowdsale_address,
                            "vmtype": 0,
                            "vmversion": 0,
                            "code": bytecode
                        }
                    }, {
                        "account": "eosio",
                        "name": "setabi",
                        "authorization": [{
                            "actor": crowdsale_address,
                            "permission": "active"
                        }],
                        "data": {
                            "account": crowdsale_address,
                            "abi": abi
                        }
                    }, {
                        "account": token_address,
                        "name": "create" if is_transferable_at_once else "createlocked",
                        "authorization": [{
                            "actor": token_address,
                            "permission": "active"
                        }],
                        "data": {
                            "issuer": crowdsale_address,
                            "maximum_supply": max_supply + " " + token_short_name,
                            "lock": not is_transferable_at_once
                        }
                    },
                    {
                        "account": crowdsale_address,
                        "name": "init",
                        "authorization": [{
                            "actor": crowdsale_address,
                            "permission": "active"
                        }],
                        "data": init_data
                    },
                    {
                        "account": "eosio",
                        "name": "updateauth",
                        "authorization": [{
                            "actor": crowdsale_address,
                            "permission": "owner"
                        }],
                        "data": {
                            "account": crowdsale_address,
                            "permission": "owner",
                            "parent": "",
                            "auth": {
                                "threshold": 1,
                                "keys": [],
                                "accounts": [{
                                    "permission": {
                                        "actor": crowdsale_address,
                                        "permission": "owner"
                                    },
                                    "weight": 1
                                }],
                                "waits": []
                            }
                        }
                    }, {
                        "account": "eosio",
                        "name": "updateauth",
                        "authorization": [{
                            "actor": crowdsale_address,
                            "permission": "active"
                        }],
                        "data": {
                            "account": crowdsale_address,
                            "permission": "active",
                            "parent": "owner",
                            "auth": {
                                "threshold": 1,
                                "keys": [],
                                "accounts": [{
                                    "permission": {
                                        "actor": crowdsale_address,
                                        "permission": "eosio.code"
                                    },
                                    "weight": 1
                                }],
                                "waits": []
                            }
                        }
                    }]
                }
