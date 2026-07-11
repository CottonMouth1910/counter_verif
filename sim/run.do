onerror {resume}
quietly WaveActivateNextPane {} 0
add wave -noupdate /counter_tb/clk
add wave -noupdate /counter_tb/rst_n
add wave -noupdate /counter_tb/en
add wave -noupdate /counter_tb/up_down
add wave -noupdate /counter_tb/count
add wave -noupdate /counter_tb/exp_count
add wave -noupdate /counter_tb/error_count
add wave -noupdate /counter_tb/dut/clk
add wave -noupdate /counter_tb/dut/rst_n
add wave -noupdate /counter_tb/dut/en
add wave -noupdate /counter_tb/dut/up_down
add wave -noupdate /counter_tb/dut/count
TreeUpdate [SetDefaultTree]
WaveRestoreCursors {{Cursor 1} {0 ps} 0}
quietly wave cursor active 0
configure wave -namecolwidth 150
configure wave -valuecolwidth 100
configure wave -justifyvalue left
configure wave -signalnamewidth 0
configure wave -snapdistance 10
configure wave -datasetprefix 0
configure wave -rowmargin 4
configure wave -childrowmargin 2
configure wave -gridoffset 0
configure wave -gridperiod 1
configure wave -griddelta 40
configure wave -timeline 0
configure wave -timelineunits ns
update
WaveRestoreZoom {0 ps} {22901 ps}


