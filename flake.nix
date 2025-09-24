{
  description = "A Nix-flake for the AdventureBoard local development environment";
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
  };
  outputs = {nixpkgs, ...}: let
    # Define the system architecture
    system = "x86_64-linux";
    # system = "x86_64-darwin";
  in {
    devShells."${system}".default = let
      pkgs = import nixpkgs {
        inherit system;
      };
    in
      pkgs.mkShell {
        packages = with pkgs; [
          nodejs
        ];

        # Shell hook that executes when the development environment starts
        shellHook = ''
          # If the shell is Fish, start a new Fish shell session to ensure proper environment setup
          if [[ "$SHELL" == *"fish"* ]]; then
            exec fish
          fi

          # If no node_modules folder exists, install the project dependencies
          if [ ! -d node_modules ]; then
            npm install
          fi
        '';
      };
  };
}
