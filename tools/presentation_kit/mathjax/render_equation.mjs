import fs from 'node:fs/promises';
import process from 'node:process';
import sharp from 'sharp';

if (process.argv.length < 3) {
  console.error('usage: node render_equation.mjs request.json');
  process.exit(2);
}

const request = JSON.parse(await fs.readFile(process.argv[2], 'utf8'));

global.MathJax = {
  loader: {
    paths: {mathjax: '@mathjax/src/bundle'},
    load: ['adaptors/liteDOM'],
    require: (file) => import(file),
  },
  svg: {fontCache: 'local'},
};

await import('@mathjax/src/bundle/tex-svg.js');
await MathJax.startup.promise;

const em = Number(request.font_size_pt) * 96 / 72;
const node = await MathJax.tex2svgPromise(request.tex, {
  display: Boolean(request.display),
  em,
  ex: em / 2,
  containerWidth: 80 * em,
});
const adaptor = MathJax.startup.adaptor;
const svgNode = adaptor.tags(node, 'svg')[0];
adaptor.setAttribute(svgNode, 'xmlns', 'http://www.w3.org/2000/svg');
adaptor.setAttribute(svgNode, 'color', String(request.color));
const mathGroup = adaptor.tags(svgNode, 'g')[0];
if (mathGroup) {
  adaptor.setAttribute(mathGroup, 'fill', String(request.color));
  adaptor.setAttribute(mathGroup, 'stroke', String(request.color));
}
const svg = '<?xml version="1.0" encoding="UTF-8"?>\n' + adaptor.serializeXML(svgNode);

await fs.writeFile(request.output_svg, svg, 'utf8');
await sharp(Buffer.from(svg), {density: Number(request.dpi)})
  .png()
  .toFile(request.output_png);

MathJax.done();
