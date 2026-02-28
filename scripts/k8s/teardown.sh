#!/usr/bin/env bash
set -euo pipefail

kubectl delete namespace fluxura --ignore-not-found=true
printf "Namespace fluxura eliminato.\n"
