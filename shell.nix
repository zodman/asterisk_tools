{
  pkgs ? import <nixpkgs> { },
}:

pkgs.mkShell {
  buildInputs = [
    pkgs.zxpy
    (pkgs.python3.withPackages (
      ps: with ps; [
        rich
      ]
    ))
  ];
}
