# ---------------------------------------------------------
# Generate Change Log and insert into simulation archive
# ---------------------------------------------------------

set changelog_tmp = "/tmp/change_log_${simulation_version}_$$.txt"
set tar_tmp_dir = "/tmp/sim_unpack_${simulation_version}_$$"

echo "Generating Change Log..."
/valfac/sim/dev/tools/create_change_log.sh /valfac/benches/a350 "$changelog_tmp"

if (-e "$changelog_tmp") then

    echo "Injecting Change Log into simulation tarball..."

    mkdir "$tar_tmp_dir"

    tar -xzf $package/simulations/${simulation_version}_for_Linux.tar.gz -C "$tar_tmp_dir"

    cp "$changelog_tmp" "$tar_tmp_dir/CHANGE_LOG.txt"

    tar -czf $package/simulations/${simulation_version}_for_Linux.tar.gz -C "$tar_tmp_dir" .

    rm -rf "$tar_tmp_dir"
    rm -f "$changelog_tmp"

else
    echo "WARNING: Change Log was not created."
endif
