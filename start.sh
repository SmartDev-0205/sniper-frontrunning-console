cd /home/ubuntu
./geth --config ./config.toml --datadir ./node  --cache 18000 --rpc.allow-unprotected-txs --txlookuplimit 0 --ws --ws.port 8546 --http