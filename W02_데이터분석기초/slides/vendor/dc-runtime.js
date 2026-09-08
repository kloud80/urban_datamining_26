/* DCLogic shim — shared by present.html and build_pdf.py.

   A Claude Design deck keeps its charts in <script type="text/x-dc">, which
   defines `class Component extends DCLogic` whose renderVals() returns a map of
   named React elements. The host app mounts those into the deck's {{ name }}
   holes; outside it neither DCLogic nor the mounting exists, so the holes render
   as literal text.

   The builders rewrite each hole to <span data-dc-slot="name"> and each
   <sc-if value="{{ k }}"> to <div data-dc-if="k">. This file supplies the
   missing base class and mounts every value through a portal, so a deck stays
   ONE React tree — that is what lets the S15 slider drive its own chart instead
   of rendering a dead snapshot.

   Several decks can share one page. Each is registered on window.DC_DECKS with
   its index, and every lookup is scoped to that deck's own slides, so two decks
   that happen to use the same slot name never mount into each other. */
window.DC_DECKS = window.DC_DECKS || [];

(function () {
  "use strict";

  window.DCLogic = class extends React.Component {
    renderVals() { return {}; }

    /* Slots live in the deck's slides, not in this component's own subtree. */
    dcScope() {
      var d = this.props.__dcDeck;
      return d === undefined ? '' : '#stage > section[data-deck="' + d + '"] ';
    }

    /* <sc-if> blocks are plain DOM outside the React tree, so they are toggled
       imperatively after each commit rather than rendered. */
    syncConditionals(vals) {
      var scope = this.dcScope();
      document.querySelectorAll(scope + '[data-dc-if]').forEach(function (el) {
        var k = el.getAttribute('data-dc-if');
        if (k in vals) el.toggleAttribute('data-dc-off', !vals[k]);
      });
    }
    componentDidMount()  { this.syncConditionals(this.renderVals()); }
    componentDidUpdate() { this.syncConditionals(this.renderVals()); }

    render() {
      var vals = this.renderVals(), out = [], i = 0;
      document.querySelectorAll(this.dcScope() + '[data-dc-slot]').forEach(function (el) {
        var k = el.getAttribute('data-dc-slot');
        if (!(k in vals)) return;
        var v = vals[k];
        if (v === null || v === undefined || typeof v === 'boolean') return;
        out.push(ReactDOM.createPortal(v, el, 'dc' + (i++)));
      });
      return React.createElement(React.Fragment, null, out);
    }
  };
})();
