// =============================================================================
// Desk Jarvis case — Orange Pi Zero 2W (bottom) + Whisplay HAT (top)
// Ethan’s desk Jarvis. Custom OPi ports (NOT RPi Micro-USB).
// OpenSCAD 2021.01+  |  mm
// =============================================================================
// PCB-local coords (origin = microSD corner of PCB footprint):
//   X 0..65  (X=0 microSD, X=65 screen/RGB end)
//   Y 0..30  (Y=0 Mini-HDMI + 2×USB-C; Y=30 GPIO/40-pin header)
//   Z up from underside of bottom PCB
 // HAT face openings informed by photos + PiSugar/Ground Zero (RPi ports ignored).
// =============================================================================

/* [Render] */
part = "both"; // ["bottom","top","both","assembly"]
explode = 0;

/* [PCB / stack] */
pcb_x = 65.0;
pcb_y = 30.0;
pcb_t = 1.2;
corner_r = 3.0;
hole_centers = [[3.5,3.5],[61.5,3.5],[3.5,26.5],[61.5,26.5]];

standoff_h = 2.0;
header_gap = 11.0;
hat_t = 1.2;
display_raise = 2.5;
cavity_h = 22.0;       // standoff tops → lid underside (≥22)

/* [Case shell] */
wall = 1.8;
floor_t = 1.8;
lid_t = 1.8;
pcb_clr = 0.5;
split_z = 14.0;        // bottom inner wall height above floor top
lip_h = 1.2;           // stepped rim for lid mate

/* [Screen — Whisplay 30×37 glass, PCB X=28..65] */
screen_x0 = 28.0;
screen_len = 37.0;
win_x = 36.0;
win_y = 29.0;
win_recess = 0.6;

/* [Whisplay face — branding zone] */
mic_d = 2.8;
mic_positions = [[12.0, 10.0],[12.0, 20.0]];
spk_cx = 14.0; spk_cy = 15.0; spk_hole_d = 1.6; spk_pitch = 2.4;
spk_rows = 3; spk_cols = 4;
led_d = 3.2; led_x = 63.5; led_y = 15.0;
btn_d = 5.5; btn_x = 20.0; btn_y = 6.0;

/* [Orange Pi Zero 2W ports] */
hdmi_x = 12.5; hdmi_w = 9.0; hdmi_h = 4.2;
usbc1_x = 40.5; usbc2_x = 53.5; usbc_w = 10.0; usbc_h = 4.0;
sd_w = 14.0; sd_h = 2.4; sd_depth = 4.0;
ant_x = 58.0; ant_z_from_pcb = 6.0; ant_d = 3.5;
ph_x = 28.0; ph_w = 8.0; ph_h = 5.0; ph_z_from_pcb = 4.0;

/* [Bosses / M2.5 — screws from bottom into lid posts] */
boss_od = 6.2;
boss_id_bottom = 2.9;
boss_id_lid = 3.2;
insert_pilot = 3.6;
use_heatset = false;
screw_head_d = 5.2;
screw_head_h = 1.8;

eps = 0.08;
$fn = 48;

inner_x = pcb_x + 2*pcb_clr;
inner_y = pcb_y + 2*pcb_clr;
outer_x = inner_x + 2*wall;
outer_y = inner_y + 2*wall;
inner_h = standoff_h + cavity_h;
outer_h = floor_t + inner_h + lid_t;
bottom_h = floor_t + split_z;          // includes full wall; lip is a STEP cut
lid_wall_h = outer_h - bottom_h + lip_h; // lid walls drop into the step
pcb_ox = wall + pcb_clr;
pcb_oy = wall + pcb_clr;
pcb_oz = floor_t + standoff_h;
lid_id = use_heatset ? insert_pilot : boss_id_lid;

module rounded_box(sx, sy, sz, r) {
    rr = min(r, sx/2 - 0.01, sy/2 - 0.01);
    linear_extrude(height=sz)
        translate([rr, rr])
            offset(r=rr) square([sx - 2*rr, sy - 2*rr], center=false);
}

module wall_slot_y0(cx, zc, w, h, depth) {
    translate([cx - w/2, -eps, zc - h/2]) cube([w, depth + eps, h]);
}
module wall_slot_x0(cy, zc, w, h, depth) {
    translate([-eps, cy - w/2, zc - h/2]) cube([depth + eps, w, h]);
}

module port_cutouts() {
    wall_slot_y0(pcb_ox + hdmi_x, pcb_oz + pcb_t + hdmi_h/2 - 0.5,
                 hdmi_w, hdmi_h, wall + pcb_clr + 1.5);
    for (ux = [usbc1_x, usbc2_x])
        wall_slot_y0(pcb_ox + ux, pcb_oz + pcb_t + usbc_h/2 - 0.8,
                     usbc_w, usbc_h, wall + pcb_clr + 1.5);
    wall_slot_x0(pcb_oy + pcb_y/2, pcb_oz + pcb_t + sd_h/2,
                 sd_w, sd_h, wall + pcb_clr + sd_depth);
    wall_slot_y0(pcb_ox + ant_x, pcb_oz + pcb_t + ant_z_from_pcb,
                 ant_d + 1.0, ant_d, wall + pcb_clr + 1.0);
    wall_slot_y0(pcb_ox + ph_x, pcb_oz + pcb_t + ph_z_from_pcb,
                 ph_w, ph_h, wall + pcb_clr + 1.0);
}

// =============================================================================
module case_bottom() {
    r_out = corner_r + pcb_clr + wall;
    r_in  = corner_r + pcb_clr;
    step = wall * 0.45;   // horizontal depth of lid seat step

    difference() {
        union() {
            // Outer shell open at top
            difference() {
                rounded_box(outer_x, outer_y, bottom_h, r_out);
                translate([wall, wall, floor_t])
                    rounded_box(inner_x, inner_y, bottom_h - floor_t + eps, max(0.2, r_in));
            }
            // PCB standoffs
            for (h = hole_centers)
                translate([pcb_ox + h[0], pcb_oy + h[1], floor_t])
                    cylinder(h=standoff_h, d=boss_od);
        }

        // Stepped rim: cut inner ledge so lid walls drop in (no overlapping add)
        translate([step, step, bottom_h - lip_h])
            rounded_box(outer_x - 2*step, outer_y - 2*step, lip_h + eps,
                        max(0.2, r_out - step));

        // Screw through + countersink from outside bottom
        for (h = hole_centers) {
            translate([pcb_ox + h[0], pcb_oy + h[1], -eps])
                cylinder(h=bottom_h + 2*eps, d=boss_id_bottom);
            translate([pcb_ox + h[0], pcb_oy + h[1], -eps])
                cylinder(h=screw_head_h + eps, d1=screw_head_d, d2=boss_id_bottom);
        }

        port_cutouts();
    }
}

// =============================================================================
module case_top() {
    r_out = corner_r + pcb_clr + wall;
    r_in  = corner_r + pcb_clr;
    step = wall * 0.45;

    difference() {
        union() {
            // Lid box (walls hang down; top slab = lid_t)
            difference() {
                rounded_box(outer_x, outer_y, lid_wall_h, r_out);
                translate([wall, wall, -eps])
                    rounded_box(inner_x, inner_y, lid_wall_h - lid_t + 0.01, max(0.2, r_in));
            }

            // Posts: overlap into slab by 1.5mm for manifold fuse
            for (h = hole_centers) {
                z_top = lid_wall_h - lid_t + 1.5;
                z_bot = 1.0;
                translate([pcb_ox + h[0], pcb_oy + h[1], z_bot])
                    cylinder(h=z_top - z_bot, d=boss_od);
            }

            // Brace screen-end posts (X=61.5) to walls — window removes slab there
            for (h = hole_centers) if (h[0] > 40) {
                cx = pcb_ox + h[0];
                cy = pcb_oy + h[1];
                z0 = 1.0;
                zh = lid_wall_h - lid_t + 1.0;
                // to X=max wall
                hull() {
                    translate([cx, cy, z0]) cylinder(h=zh-z0, d=boss_od*0.85);
                    translate([outer_x - wall - 0.05, cy - boss_od*0.3, z0])
                        cube([wall*0.55, boss_od*0.6, zh-z0]);
                }
                // to nearer Y wall
                if (h[1] < pcb_y/2)
                    hull() {
                        translate([cx, cy, z0]) cylinder(h=zh-z0, d=boss_od*0.85);
                        translate([cx - boss_od*0.3, 0.15, z0])
                            cube([boss_od*0.6, wall*0.9, zh-z0]);
                    }
                else
                    hull() {
                        translate([cx, cy, z0]) cylinder(h=zh-z0, d=boss_od*0.85);
                        translate([cx - boss_od*0.3, outer_y - wall*0.9 - 0.15, z0])
                            cube([boss_od*0.6, wall*0.9, zh-z0]);
                    }
            }
        }

        // Pilot holes (open from bottom of lid, stop before outer top skin)
        for (h = hole_centers)
            translate([pcb_ox + h[0], pcb_oy + h[1], -eps])
                cylinder(h=lid_wall_h - 0.8, d=lid_id);

        // Screen window
        win_x0 = pcb_ox + screen_x0 + (screen_len - win_x)/2;
        win_y0 = pcb_oy + (pcb_y - win_y)/2;
        translate([win_x0, win_y0, lid_wall_h - lid_t - eps])
            cube([win_x, win_y, lid_t + 2*eps]);
        translate([win_x0 - 0.5, win_y0 - 0.5, lid_wall_h - lid_t - eps])
            cube([win_x + 1.0, win_y + 1.0, win_recess + eps]);

        // Mic / speaker / LED / button
        for (m = mic_positions)
            translate([pcb_ox + m[0], pcb_oy + m[1], lid_wall_h - lid_t - eps])
                cylinder(h=lid_t + 2*eps, d=mic_d);
        for (i = [0:spk_cols-1])
            for (j = [0:spk_rows-1])
                translate([
                    pcb_ox + spk_cx + (i - (spk_cols-1)/2)*spk_pitch,
                    pcb_oy + spk_cy + (j - (spk_rows-1)/2)*spk_pitch,
                    lid_wall_h - lid_t - eps
                ]) cylinder(h=lid_t + 2*eps, d=spk_hole_d);
        translate([pcb_ox + led_x, pcb_oy + led_y, lid_wall_h - lid_t - eps])
            cylinder(h=lid_t + 2*eps, d=led_d);
        translate([pcb_ox + btn_x, pcb_oy + btn_y, lid_wall_h - lid_t - eps])
            cylinder(h=lid_t + 2*eps, d=btn_d);

        // Mate: thin outer skirt seats into bottom step
        // (remove inner material at wall foot so remaining wall thickness = step)
        translate([step, step, -eps])
            rounded_box(outer_x - 2*step, outer_y - 2*step, lip_h + 0.15,
                        max(0.2, r_out - step));
    }
}

module print_layout() {
    case_bottom();
    translate([outer_x + 8, 0, 0])
        translate([0, outer_y, lid_wall_h])
            rotate([180, 0, 0])
                case_top();
}

if (part == "bottom") case_bottom();
else if (part == "top")
    translate([0, outer_y, lid_wall_h]) rotate([180, 0, 0]) case_top();
else if (part == "assembly") {
    case_bottom();
    translate([0, 0, bottom_h - lip_h + explode]) case_top();
} else print_layout();

echo(str("outer=", outer_x, "x", outer_y, "x", outer_h));
echo(str("bottom_h=", bottom_h, " lid_wall_h=", lid_wall_h, " cavity=", cavity_h));
