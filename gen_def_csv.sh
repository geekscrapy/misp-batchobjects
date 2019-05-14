#!/bin/bash
echo "This builds a CSV file with all available object fields populated"

read -p "CSV file to write to [def. is '"$PWD"/all.csv']: " csvfile
if [[ "$csvfile" == "" ]]; then
    csvfile="$PWD/all.csv";
fi
csvfile=$(realpath $csvfile)

read -p "MISP objects path: [blank for none]: " mpath
if [[ "$mpath" != "" ]]; then
    cd $mpath; jq -r '[ .attributes | to_entries[] | .key]' $(find -name *.json) | jq -s add | jq -r ' . | map(select(. != "comment")) | sort | unique | ["object","comment"] + . | @csv' > $csvfile
fi

read -p "Custom objects path: [blank for none]: " cpath
if [[ "$cpath" != "" ]]; then
    cd $cpath; jq -r '[ .attributes | to_entries[] | .key]' $(find -name *.json) | jq -s add | jq -r ' . | map(select(. != "comment")) | sort | unique | @csv' >> $csvfile
fi

if [[ $(wc -l <"$csvfile") -lt 1 ]]; then
    echo "Failed to gather objects"
    exit 1
fi

cat $csvfile | tr '\n' ',' > $csvfile.new
mv $csvfile.new $csvfile

echo "Written to" $csvfile
