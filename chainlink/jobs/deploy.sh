
sudo cat /opt/chainlinknode/jobs/exchange_rate_job.template | envsubst | sudo tee /opt/chainlinknode/sample_job.toml
sudo jq -Rs "{toml:.}" /opt/chainlinknode/sample_job.toml | sudo tee /opt/chainlinknode/sample_job.json
sudo curl -c ./cookie -H "content-type:application/json" -d @/opt/chainlinknode/api.json localhost:6688/sessions
sudo curl -b ./cookie -c ./cookie -H "content-type:application/json" -d @/opt/chainlinknode/sample_job.json http://localhost:6688/v2/jobs
