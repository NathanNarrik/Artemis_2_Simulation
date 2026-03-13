# ---------------------------------------------------------
# Generate Change Log and insert into simulation archive
# ---------------------------------------------------------

set change_log_tmp = "/tmp/change_log_${simulation_version}_$$.txt"
set tar_tmp_dir = "/tmp/sim_unpack_${simulation_version}_$$"
set tar_new = "/tmp/sim_new_${simulation_version}_$$.tar.gz"

echo "Generating Change Log..."
/valfac/sim/dev/tools/change_log.sh /valfac/sim/dev/a350 "$change_log_tmp"

if (-e "$change_log_tmp") then
    echo "Adding Change Log to package..."

    mkdir -p "$tar_tmp_dir"

    tar -xzf $package/simulations/${simulation_version}_for_Linux.tar.gz -C "$tar_tmp_dir"

    # Find the top-level directory inside the extracted simulation tarball
    set sim_root = `ls "$tar_tmp_dir" | head -1`

    if (-d "$tar_tmp_dir/$sim_root") then
        cp "$change_log_tmp" "$tar_tmp_dir/$sim_root/CHANGE_LOG.txt"
    else
        # Fallback: if archive does not unpack into a single top-level directory
        cp "$change_log_tmp" "$tar_tmp_dir/CHANGE_LOG.txt"
    endif

    tar -czf "$tar_new" -C "$tar_tmp_dir" .
    mv "$tar_new" $package/simulations/${simulation_version}_for_Linux.tar.gz

    rm -rf "$tar_tmp_dir"
    rm -f "$change_log_tmp"
else
    echo "WARNING: Change Log was not created."
endif
