variable "CISE_IMAGE" {
  default = "cise/erpnext-hrms"
}

variable "CISE_TAG" {
  default = "f16.29.0-e16.30.0-h16.17.1-via0.5.10"
}

variable "CISE_BASE_IMAGE" {
  default = "cise/erpnext-hrms:f16.29.0-e16.30.0-h16.17.1-via0.5.9"
}

group "default" {
  targets = ["cise"]
}

target "cise" {
  context    = "."
  dockerfile = "images/custom/Containerfile.erpweb-overlay"
  target     = "backend"
  tags       = ["${CISE_IMAGE}:${CISE_TAG}"]

  contexts = {
    erpweb        = "../ERPWeb"
    cyce_viaticos = "./custom_apps/cyce_viaticos"
  }

  args = {
    BASE_IMAGE = "${CISE_BASE_IMAGE}"
  }
}
