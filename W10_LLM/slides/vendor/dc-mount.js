/* Mount every registered deck. Must load AFTER the deck scripts.

   Props come from each deck's own data-props defaults — the same values the
   Claude Design host would have passed in.

   <sc-if> visibility is also resolved here, straight from those props, rather
   than relying on DCLogic.componentDidMount: a deck may override that hook for
   its own purposes (기계학습의 역사 uses it to drive its GIFs) and never call
   super, which would leave its conditional blocks unresolved.

   Sets document.documentElement.dataset.dcReady once the first paint is done so
   a headless renderer can wait for the charts instead of guessing a timeout. */
(function () {
  "use strict";
  var decks = window.DC_DECKS || [];

  decks.forEach(function (d) {
    var scope = '#stage > section[data-deck="' + d.deck + '"] ';
    Object.keys(d.props || {}).forEach(function (k) {
      document.querySelectorAll(scope + '[data-dc-if="' + k + '"]').forEach(function (el) {
        el.toggleAttribute('data-dc-off', !d.props[k]);
      });
    });
    if (typeof d.Component !== 'function') return;
    var host = document.createElement('div');
    host.style.display = 'none';
    document.body.appendChild(host);
    var props = Object.assign({}, d.props, { __dcDeck: d.deck });
    ReactDOM.createRoot(host).render(React.createElement(d.Component, props));
  });

  requestAnimationFrame(function () {
    requestAnimationFrame(function () {
      document.documentElement.dataset.dcReady = '1';
    });
  });
})();
