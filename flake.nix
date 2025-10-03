{
  description = "A Nix-flake for the AdventureBoard local development environment";
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
  };
  outputs =
    { nixpkgs, ... }:
    let
      # Define the supported systems
      systems = [
        "x86_64-linux"
        "x86_64-darwin"
      ];

      # Define the development shell for the specified system
      devShellsBySys = builtins.listToAttrs (
        map (system: {
          name = system;
          value = {
            default =
              let
                pkgs = import nixpkgs { inherit system; };
              in
              pkgs.mkShell {
                name = "impurePythonEnv";
                venvDir = "./.venv";

                buildInputs = with pkgs; [
                  mask
                  nodejs
                  python313
                  python313Packages.venvShellHook
                  sqlite
                ];

                postVenvCreation = ''
                  unset SOURCE_DATE_EPOCH
                  cd board && pip install -r requirements.txt
                '';

                postShellHook = ''
                  # allow pip to install wheels
                  unset SOURCE_DATE_EPOCH
                '';
              };
          };
        }) systems
      );
    in
    {
      devShells = devShellsBySys // {
        default = devShellsBySys."${builtins.currentSystem}".default;
      };
    };
}
