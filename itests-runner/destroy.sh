#!/bin/bash

pushd work

terraform destroy -force -var-file inputs.json
exit_code=$?

popd

if [ "${exit_code}" -eq "0" ]; then
	echo "Deleting work dir.."
	rm -rf work
	echo "Done!"
else
	echo "Terraform destroy failed."
fi

