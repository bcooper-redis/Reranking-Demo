import { useEffect, useState } from "react";
import type { ChangeEvent, CSSProperties } from "react";

import {
  deleteRetailer,
  getActiveRetailerId,
  getPublicConfig,
  importRetailer,
  setActiveRetailerId,
  type PublicConfig,
  type RetailerImportPayload,
  type RetailerImportResponse,
} from "../api/search";
import { getRetailerExperience } from "../retailers";

const CATALOG_PROMPT = `Create and attach a downloadable file named [COMPANY DOMAIN]-demo-catalog.json for a synthetic product-discovery demo based on the public website for [COMPANY DOMAIN].

Put the JSON only in the downloadable file. In your chat response, confirm the file is attached but do not print the JSON. Do not use Markdown, comments, images, copyrighted descriptions, live prices, inventory claims, or private data. Create exactly 360 plausible synthetic products that illustrate the company categories and brands. Use short original descriptions.

Also create a demo_paths object from the catalog you generate. These are intentional e-commerce demo prompts: customer_query should be a natural shopper request, exact_product_query must exactly match a generated product name or alias, and preference_query should be a shopper request that can benefit from the chosen category. preference_category must exactly match one category value used in the products. Make every prompt well-supported by the generated products.

The prefix demo is required. Choose a short one-word prefix_query that has two deliberately different outcomes: at least one non-target product must contain it as a full literal word, while prefix_expected_product must begin with it but must not contain it as a full word. For example, Star can surface entertainment content before a prefix lookup reveals Starbucks. Do not put the short prefix itself in the expected product's aliases or description.

Use this exact shape:
{
  "organization_name": "Company name",
  "experience_name": "Company Product Discovery",
  "catalog_label": "products",
  "theme": {
    "accent": "#123456",
    "accent_strong": "#0A2340",
    "accent_soft": "#EAF2F8",
    "canvas": "#F7F9FA"
  },
  "demo_paths": {
    "customer_query": "durable outdoor gear for a weekend camping trip",
    "exact_product_query": "Summit Trail Daypack",
    "preference_query": "a gift for an avid camper",
    "preference_profile_name": "Camping Enthusiast",
    "preference_category": "Camping & Hiking",
    "prefix_query": "star",
    "prefix_expected_product": "Starbucks eGift"
  },
  "products": [
    {
      "brand_name": "Synthetic Product Name",
      "description": "An original, concise description of the product and shopping intent.",
      "aliases": ["search phrase", "brand shorthand"],
      "categories": ["category"],
      "recipient_tags": ["shopper persona"],
      "delivery_types": ["shipping", "pickup"],
      "min_price": 25,
      "max_price": 120
    }
  ]
}`;

export function DemoConfigurationPage() {
  const [config, setConfig] = useState<PublicConfig | null>(null);
  const [selectedRetailer, setSelectedRetailer] = useState(
    getActiveRetailerId(),
  );
  const [importPayload, setImportPayload] = useState<RetailerImportPayload | null>(
    null,
  );
  const [demoName, setDemoName] = useState("");
  const [importStatus, setImportStatus] = useState("");
  const [importError, setImportError] = useState("");
  const [promptStatus, setPromptStatus] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [isDeleteConfirming, setIsDeleteConfirming] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [generatedRetailer, setGeneratedRetailer] =
    useState<RetailerImportResponse | null>(null);

  useEffect(() => {
    void getPublicConfig().then((nextConfig) => {
      setConfig(nextConfig);
      setSelectedRetailer(nextConfig.retailer.id);
    });
  }, []);

  const experience = getRetailerExperience(
    selectedRetailer,
    config?.retailer.theme ?? null,
    config?.retailer.demo_prompts ?? null,
  );
  const canDeleteSelectedRetailer = Boolean(config?.retailer.theme);

  function chooseRetailer(retailerId: string) {
    setActiveRetailerId(retailerId);
    setSelectedRetailer(retailerId);
    void getPublicConfig().then(setConfig);
  }

  async function loadCatalogFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setImportError("");
    setImportStatus("");
    setGeneratedRetailer(null);
    try {
      const parsed = JSON.parse(await file.text()) as RetailerImportPayload;
      if (!Array.isArray(parsed.products) || parsed.products.length !== 360) {
        throw new Error("The file needs exactly 360 products.");
      }
      setImportPayload(parsed);
      setDemoName(parsed.experience_name ?? "");
      setImportStatus(`${parsed.products.length} products ready for generation.`);
    } catch (error) {
      setImportPayload(null);
      setImportError(
        error instanceof Error ? error.message : "The catalog file could not be read.",
      );
    }
  }

  async function generateRetailer() {
    if (!importPayload || !demoName.trim()) return;
    setImportError("");
    setGeneratedRetailer(null);
    setIsGenerating(true);
    setImportStatus("Creating the isolated Redis catalog and search index...");
    try {
      const created = await importRetailer({
        ...importPayload,
        experience_name: demoName.trim(),
      });
      setActiveRetailerId(created.retailer_id);
      setSelectedRetailer(created.retailer_id);
      const nextConfig = await getPublicConfig();
      setConfig(nextConfig);
      setGeneratedRetailer(created);
      setImportStatus(
        `${created.catalog_count} products indexed in ${created.index_alias}.`,
      );
    } catch (error) {
      setImportError(
        error instanceof Error ? error.message : "The retailer could not be generated.",
      );
    } finally {
      setIsGenerating(false);
    }
  }

  async function removeRetailer() {
    setIsDeleting(true);
    setImportError("");
    try {
      await deleteRetailer(selectedRetailer);
      setActiveRetailerId("bhn");
      setSelectedRetailer("bhn");
      setGeneratedRetailer(null);
      setIsDeleteConfirming(false);
      setImportStatus("Custom demo deleted. Blackhawk Networks is selected.");
      const nextConfig = await getPublicConfig();
      setConfig(nextConfig);
    } catch (error) {
      setImportError(
        error instanceof Error ? error.message : "The retailer could not be deleted.",
      );
    } finally {
      setIsDeleting(false);
    }
  }

  async function copyCatalogPrompt() {
    try {
      await navigator.clipboard.writeText(CATALOG_PROMPT);
      setPromptStatus("Prompt copied to clipboard.");
    } catch {
      setPromptStatus("Clipboard access was unavailable. Select the prompt text to copy it.");
    }
  }

  return (
    <main
      className="configuration-page"
      style={
        {
          "--retailer-accent": experience.theme.accent,
          "--retailer-accent-strong": experience.theme.accentStrong,
          "--retailer-ink": experience.theme.ink,
          "--retailer-muted": experience.theme.muted,
          "--retailer-panel": experience.theme.panel,
          "--retailer-border": experience.theme.border,
          "--retailer-canvas": experience.theme.canvas,
        } as CSSProperties
      }
    >
      <header className="configuration-header">
        <p className="eyebrow">Internal demo configuration</p>
        <h1>Prepare a retailer experience</h1>
        <p>
          Choose the isolated retailer context for this browser before opening
          the demo.
        </p>
      </header>
      <section
        className="configuration-tool"
        aria-labelledby="configuration-heading"
      >
        <h2 id="configuration-heading">Retailer context</h2>
        <label>
          <span>Retailer</span>
          <select
            onChange={(event) => chooseRetailer(event.target.value)}
            value={selectedRetailer}
          >
            {config?.retailers.map((retailer) => (
              <option key={retailer.id} value={retailer.id}>
                {retailer.organization_name}
              </option>
            ))}
          </select>
        </label>
        <dl className="configuration-details">
          <div>
            <dt>Experience</dt>
            <dd>{config?.retailer.experience_name ?? "Loading"}</dd>
          </div>
          <div>
            <dt>Redis namespace</dt>
            <dd>Isolated per retailer</dd>
          </div>
        </dl>
        <button onClick={() => window.location.assign("/")} type="button">
          Open prepared demo
        </button>
        {canDeleteSelectedRetailer && !isDeleteConfirming && (
          <button
            className="delete-demo-button"
            onClick={() => setIsDeleteConfirming(true)}
            type="button"
          >
            Delete custom demo
          </button>
        )}
        {canDeleteSelectedRetailer && isDeleteConfirming && (
          <div className="delete-confirmation" role="alert">
            <p>
              Delete this custom demo and its isolated Redis catalog, search index, and
              routing data?
            </p>
            <div>
              <button onClick={() => setIsDeleteConfirming(false)} type="button">
                Keep demo
              </button>
              <button
                className="delete-demo-button"
                disabled={isDeleting}
                onClick={() => void removeRetailer()}
                type="button"
              >
                {isDeleting ? "Deleting demo..." : "Delete demo"}
              </button>
            </div>
          </div>
        )}
      </section>
      <section
        className="configuration-tool demo-foundry"
        aria-labelledby="foundry-heading"
      >
        <div>
          <p className="eyebrow">On-the-fly retailer</p>
          <h2 id="foundry-heading">Demo foundry</h2>
        </div>
        <p>
          Generate a downloadable catalog file with ChatGPT, then upload it to
          create a fresh retailer namespace without rebuilding the application.
        </p>
        <details>
          <summary>ChatGPT catalog prompt</summary>
          <button
            aria-label="Copy ChatGPT catalog prompt"
            className="copy-prompt-button"
            onClick={() => void copyCatalogPrompt()}
            type="button"
          >
            Copy prompt
          </button>
          {promptStatus && <p className="prompt-status">{promptStatus}</p>}
          <textarea
            aria-label="ChatGPT catalog prompt"
            readOnly
            value={CATALOG_PROMPT}
          />
        </details>
        <label>
          <span>Catalog file</span>
          <input
            accept=".json,.txt,application/json,text/plain"
            onChange={loadCatalogFile}
            type="file"
          />
        </label>
        <label>
          <span>Demo name</span>
          <input
            disabled={!importPayload}
            onChange={(event) => setDemoName(event.target.value)}
            placeholder="Company Product Discovery"
            value={demoName}
          />
        </label>
        {importStatus && <p className="configuration-status">{importStatus}</p>}
        {importError && <p className="configuration-error">{importError}</p>}
        {generatedRetailer && (
          <section className="generation-complete" aria-live="polite">
            <p className="label">Generation complete</p>
            <h3>{generatedRetailer.experience_name} is ready</h3>
            <p>
              {generatedRetailer.catalog_count} products are indexed in an isolated
              Redis namespace.
            </p>
            <code>{generatedRetailer.index_alias}</code>
            <button onClick={() => window.location.assign("/")} type="button">
              Open generated demo
            </button>
          </section>
        )}
        <button
          disabled={!importPayload || !demoName.trim() || isGenerating}
          onClick={() => void generateRetailer()}
          type="button"
        >
          {isGenerating ? "Generating retailer demo..." : "Generate retailer demo"}
        </button>
      </section>
    </main>
  );
}
