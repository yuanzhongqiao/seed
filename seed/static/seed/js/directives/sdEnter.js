/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 *
 * Directive sd-enter used for search or filter input to only fire on 'enter' or 'return'
 */
angular.module('sdEnter', []).directive(
  'sdEnter',
  () => (scope, element, attrs) => {
    element.bind('keydown keypress', (event) => {
      if (event.which === 13) {
        scope.$apply(() => {
          scope.$eval(attrs.sdEnter);
        });
        event.preventDefault();
      }
    });
  }
);
