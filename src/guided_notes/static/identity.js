/* All identity information is server escaped. Keep status rendering safe for
   progressive-enhancement consumers without requiring JavaScript to sign in. */
(function (root) {
  function label(identity) {
    return identity && (identity.display_name || identity.email) || 'Google 教師';
  }
  function render(node, identity) { node.textContent = label(identity); }
  if (typeof module !== 'undefined') module.exports = {label, render};
  else root.GuidedNotesIdentity = {label, render};
})(globalThis);
