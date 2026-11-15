package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"github.com/eosaios/eos/pkg/coreapi/sidecar"
	"os"
	"strings"
)

func main() {
	manifest := flag.String("manifest", "", "signed manifest")
	platform := flag.String("platform", "", "os-arch")
	flag.Parse()
	parts := strings.SplitN(*platform, "-", 2)
	if len(parts) != 2 {
		panic("invalid platform")
	}
	os.Unsetenv(sidecar.EnvCorePath)
	result, err := sidecar.ResolveBinary(sidecar.ResolveOptions{ManifestPath: *manifest, GOOS: parts[0], GOARCH: parts[1], VerifyChecksum: true, RequireSignature: true})
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	if result.Manifest == nil {
		panic("signature verification did not resolve a manifest")
	}
	json.NewEncoder(os.Stdout).Encode(map[string]any{"verified": true, "target": result.Target, "sha256": result.Manifest.SHA256})
}
