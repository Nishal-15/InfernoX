// Stub replacement for @spz-loader/core to prevent WebAssembly octal escape syntax errors in Next.js bundle
export async function loadSpz() {
  throw new Error("SPZ Gaussian Splat loader is not used in InfernoX");
}

export default {
  loadSpz,
};
