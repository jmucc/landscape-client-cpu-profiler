resource "lxd_cached_image" "noble-vm" {
    source_remote = "ubuntu"
    source_image = "noble/amd64"
    type = "virtual-machine"
}

resource "lxd_cached_image" "noble-container" {
    source_remote = "ubuntu"
    source_image = "noble/amd64"
    type = "container"
}

resource "lxd_instance" "server" {
    name  = "tf-landscape-server-noble"
    image = lxd_cached_image.noble-container.fingerprint
    type = "container"

    execs = {
        "0000-install-prereqs" = {
            command = [
                "/bin/bash", "-c",
                "apt-get update && apt-get install -y ca-certificates software-properties-common"
            ]
            trigger       = "once"
            record_output = true
            fail_on_error = true
        },
        "0001-add-ppa" = {
            command = [
                "/bin/bash", "-c", "add-apt-repository -y ${var.server-ppa}"
            ]
            record_output = true
            fail_on_error = true
        },
        "0002-install-server" = {
            command = [
                "/bin/bash", "-c",
                "DEBIAN_FRONTEND=noninteractive apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y landscape-server-quickstart --no-install-recommends"
            ]
            record_output = true
            fail_on_error = true
        }
    }

    timeouts = {
        read   = "15m"
        create = "15m"
        update = "15m"
        delete = "15m"
    }
}

resource "lxd_instance" "client" {
    name  = "tf-landscape-client-noble"
    image = lxd_cached_image.noble-vm.fingerprint
    type = "virtual-machine"

    limits = {
        cpu = 1
    }

    execs = {
      "000-pro-attach" = {
        command       = ["/bin/bash", "-c", "pro attach ${var.pro_token}"]
        trigger       = "once"
        record_output = true
        fail_on_error = true
      },
      "001-add-ppa" = {
        enabled       = var.client-ppa != null
        command       = var.client-ppa != null ? ["/bin/bash", "-c", "add-apt-repository ${var.client-ppa}"] : [""]
        trigger       = "once"
        record_output = true
        fail_on_error = true
      }
      "002-install-client" = {
        command = [
          "/bin/bash", "-c",
          "apt-get update && apt-get install -y ${var.landscape_client_package}"
        ]
        trigger       = "once"
        record_output = true
        fail_on_error = true
      },
    }

    timeouts = {
        read   = "15m"
        create = "15m"
        update = "15m"
        delete = "15m"
    }
}
