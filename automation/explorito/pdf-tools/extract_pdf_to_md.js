const fs = require('fs');
const path = require('path');
const pdf = require('pdf-parse');

async function main() {
  const [,, inPath, outPath] = process.argv;
  if (!inPath || !outPath) {
    console.error('Usage: node extract_pdf_to_md.js <in.pdf> <out.md>');
    process.exit(2);
  }
  const dataBuffer = fs.readFileSync(inPath);
  const data = await pdf(dataBuffer);

  const text = (data.text || '').replace(/\r\n/g,'\n');
  const header = `# Extracted text\n\n- Source: ${path.basename(inPath)}\n- Pages: ${data.numpages || 'unknown'}\n\n---\n\n`;
  fs.writeFileSync(outPath, header + text, 'utf8');
}

main().catch((e)=>{ console.error(e); process.exit(1); });
