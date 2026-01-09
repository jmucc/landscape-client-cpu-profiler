# Landscape Client CPU Profiling

## Inputs
* LXD container image of a Landscape Server installation with autoregistration enabled
  * Export the name of the container as environment variable `SERVER_CONTAINER_IMAGE_NAME` 
  * Export the registration key as environment variable `REGISTRATION_KEY`
* LXD VM image of a Landscape Client installation with a pro token attached

## Profiling
Run the profiler. You can configure the amount of ~1 second iterations by supplying a command line argument.
```
./profile.sh [profiling_iterations]
```

<br />

You will be asked to supply the names of your client and server images. Alternatively you can supply them in `terraform.tfvars` by editing the example filing and renaming it.
```
mv terraform.tfvars.example terraform.tfvars
```

## Outputs
* CPU Usage
* Client package database size
* Array lengths from `computer_packages` table
* Array lengths from `computer_packages_buffer` table
