{
  pkgs ? import <nixpkgs> { },
}:

let
  pythonPackages = pkgs.python313Packages;

  # 1. Corrected reusable function
  buildGitHubPackage =
    {
      owner,
      repo,
      rev,
      hash,
      pname,
      dependencies ? [ ],
    }:
    pythonPackages.buildPythonPackage {
      inherit pname;
      version = "latest";

      # Define src once here
      src = pkgs.fetchFromGitHub {
        inherit
          owner
          repo
          rev
          hash
          ;
      };

      pyproject = true;
      build-system = [ pythonPackages.setuptools ];
      propagatedBuildInputs = dependencies;
      doCheck = false;

      # Fix for the bytecode/cache collision error
      postInstall = ''
        find $out -name "__pycache__" -type d -exec rm -rf {} +
      '';
    };

  # 2. Define your packages using the helper
  pygrok = buildGitHubPackage {
    pname = "pygrok";
    owner = "garyelephant";
    repo = "pygrok";
    rev = "master";
    hash = "sha256-F4pFqKITaPPZnNt0ixXQDloOsGtammHXV4mbg/ltR64";
    dependencies = [
      pythonPackages.regex
      pythonPackages.setuptools
    ];
  };

  zxpy = buildGitHubPackage {
    pname = "zxpy";
    owner = "tusharsadhwani";
    repo = "zxpy";
    rev = "master";
    hash = "sha256-/VITHN517lPUmhLYgJHBYYvvlJdGg2Hhnwk47Mp9uc0=";
    dependencies = [ ];
  };

  # 3. Final environment
  pythonEnv = pkgs.python313.withPackages (ps: [
    ps.rich
    pygrok
    zxpy
  ]);

in
pkgs.mkShell {
  buildInputs = [
    pythonEnv
    pkgs.git
  ];

  shellHook = ''
    export PYTHONDONTWRITEBYTECODE=1
    echo "❄️  Nix environment active"
  '';
}
