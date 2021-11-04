import os

# docker ps
shit = """
0nliner/mywish_backend__base_container   latest                5fe2e5b1975a   14 minutes ago   3.05GB
0nliner/new_reciever                     latest                b26e62f78abb   2 hours ago      3.05GB
<none>                                   <none>                41501a320449   2 hours ago      3.05GB
0nliner/mywish_bot                       latest                86debd7a33b3   3 hours ago      3.05GB
0nliner/mywish_backend                   1.0                   fbb7a42b53ef   4 hours ago      3.05GB
0nliner/mywish_backend__base_container   1.0                   c4ba87e62213   4 hours ago      3.05GB
<none>                                   <none>                f22631f9c35a   5 hours ago      2.42GB
bitnami/rabbitmq                         latest                feec9c5d5f8a   14 hours ago     228MB
rabbitmq                                 3-management-alpine   1653da0c2c4d   4 days ago       177MB
<none>                                   <none>                cd0ccd225011   5 days ago       1.31GB
0nliner/my_will_scanner                  latest                4d1613f7cafb   9 days ago       1.88GB
0nliner/my_wish_dev                      latest                4d1613f7cafb   9 days ago       1.88GB
"""


# docker container ls -a
shit_lines = shit.split("\n")
for shit_line in shit_lines[1:-2]:
    shit_image_id = [govno for govno in shit_line.split(" ") if len(govno) > 0][2]
    try:
        os.system(f"docker image rm {shit_image_id}")
    except Exception:
        print(f"shit is not deleted {shit_image_id}")
