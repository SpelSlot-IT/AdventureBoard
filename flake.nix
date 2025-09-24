{
  description = "A Nix-flake for the AdventureBoard local development environment";
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
  };
  outputs =
    { nixpkgs, ... }:
    let
      # Define the system architecture
      system = "x86_64-linux";
      # system = "x86_64-darwin";
    in
    {
      devShells."${system}".default =
        let
          pkgs = import nixpkgs {
            inherit system;
          };
        in
        pkgs.mkShell {
          name = "impurePythonEnv";
          venvDir = "./.venv";

          buildInputs = with pkgs; [
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
}
