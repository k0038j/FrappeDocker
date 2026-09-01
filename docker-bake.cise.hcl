variable "CISE_IMAGE" {
  default = "cise/erpnext-hrms"
}

variable "CISE_TAG" {
  default = "f16.29.0-e16.30.0-h16.17.1"
}

group "default" {
  targets = ["cise"]
}

target "cise" {
  context    = "."
  dockerfile = "images/custom/Containerfile"
  target     = "backend"
  tags       = ["${CISE_IMAGE}:${CISE_TAG}"]

  args = {
    PYTHON_VERSION       = "3.14.2"
    NODE_VERSION         = "24.13.0"
    DEBIAN_BASE          = "bookworm"
    WKHTMLTOPDF_VERSION  = "0.12.6.1-3"
    WKHTMLTOPDF_DISTRO   = "bookworm"
    INSTALL_CHROMIUM     = "true"
    FRAPPE_PATH          = "https://github.com/frappe/frappe.git"
    FRAPPE_BRANCH        = "v16.29.0"
    FRAPPE_EXPECTED_SHA  = "06613fc60b44d5736007ae3107cdab029b2ae045"
    ERPNEXT_EXPECTED_SHA = "8378b6e203841c056925420cc44e6d631c915cf1"
    HRMS_EXPECTED_SHA    = "e1481b5cd038657d82357d91a2d81cc84c707016"
  }

  secret = ["id=apps_json,src=apps.json"]
}
