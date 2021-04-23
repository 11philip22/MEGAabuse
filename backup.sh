MEGAabuseDir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

number=0
filename=backup.tar.gz
while [ -e "$filename" ]; do
    printf -v filename 'backup_%02d.tar.gz' "$(( ++number ))"
done
printf 'Will use "%s" as filename\n' "$filename"

tar -czf "$MEGAabuseDir"/"$filename" \
         "$MEGAabuseDir"/logs "$MEGAabuseDir"/resume "$MEGAabuseDir"/accounts.txt \
         "$MEGAabuseDir"/out.json "$MEGAabuseDir"/out.txt "$MEGAabuseDir"/done.txt