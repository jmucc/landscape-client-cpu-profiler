## Landscape Client CPU Profiling

1. Paste your pro token from https://ubuntu.com/pro/dashboard into `terraform.tfvars.example` and then remove the `.example` extension.
```
mv terraform.tfvars.example terraform.tfvars
```
2. Provision architecture with terraform
```
terraform init
terraform apply -auto-approve
```
3. Creat an account on the landscape server machine and enable autoregistration with key="landscape"
4. Publish lxc images for reusability
```
./publish.sh
```
5. Run the profiler
```
./profile.sh
```
6. Examine the results in `cpu_usage_<date>.log`

Reset the profiler with fresh client and server lxc machines with `./reset/sh`. This script will tear down your machines and redeploy based on the published images `tf-landscape-server-noble` and `tf-landscape-client-noble`
