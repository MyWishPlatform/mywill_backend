import os

# docker ps
shit = """
mywill_scanner_backend       latest    08bb1884788d   3 days ago     1.7GB
<none>                       <none>    144bbcc3d5a4   3 days ago     1.32GB
<none>                       <none>    ad4399a0d19d   3 days ago     1.83GB
<none>                       <none>    6c35c2e80bbb   3 days ago     1.83GB
mywish_backend               latest    920004812317   3 days ago     1.83GB
<none>                       <none>    a358aadc0676   3 days ago     1.83GB
<none>                       <none>    4a738d6e21cf   3 days ago     1.31GB
<none>                       <none>    9c76f9422a28   4 days ago     1.31GB
<none>                       <none>    9430acd73593   4 days ago     1.31GB
<none>                       <none>    02f1eac8f18f   4 days ago     1.31GB
<none>                       <none>    49336babae3d   4 days ago     1.31GB
<none>                       <none>    52ecc4412f09   5 days ago     1.31GB
<none>                       <none>    cd0ccd225011   5 days ago     1.31GB
mywill_scanner_scanner       latest    99131663f676   6 days ago     1.88GB
0nliner/my_will_scanner      latest    4d1613f7cafb   9 days ago     1.88GB
0nliner/my_wish_dev          latest    4d1613f7cafb   9 days ago     1.88GB
mywill_scanner_db_2          latest    491c64465721   9 days ago     374MB
metagoofil                   latest    abf5b2e20372   2 weeks ago    926MB
python                       3         c05c608cfa20   2 weeks ago    915MB
imprint_v2_service_backend   latest    8890808b86d4   3 weeks ago    1.13GB
imprint_v2_db                latest    548c7ff78a5a   3 weeks ago    374MB
imprint_backend              latest    db9e59d7a45c   3 weeks ago    1.11GB
mywill_backend               latest    c67afb8597fb   3 weeks ago    1.31GB
python                       3.6       0c8ae2a24dca   3 weeks ago    902MB
python                       3.7       58c144612af4   3 weeks ago    903MB
prom/prometheus              latest    227ae20e1b04   3 weeks ago    193MB
"""


# docker container ls -a
shit_lines = shit.split("\n")
for shit_line in shit_lines[1:-2]:
    shit_image_id = [govno for govno in shit_line.split(" ") if len(govno) > 0][2]
    os.system(f"docker image rm {shit_image_id}")

