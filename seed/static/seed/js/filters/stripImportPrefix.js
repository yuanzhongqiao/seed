/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 *
 * filter 'stripImportPrefix' for custom parsing of building
 * ontology items like year built
 */
angular.module('stripImportPrefix', []).filter(
  'stripImportPrefix',
  () => (input) => {
    /** ids are sometime prefixed by the Import Record id.
       * e.g., import 28 would prefix all assessor data ids with 'IMP28-' and
       *      stripImportPrefix would strip out the 'IMP28-'s from the html and only
       *      display the ids.
       *
       * Usage: building.id = "IMP12-007"
       *        HTML: <span> {$ building.id | stripImportPrefix $} </span>
       *         compiles to: <span> 007 </span>
       *        JS  : stripImportPrefix(building.id)
       *         returns: "007"
       */
    if (_.isNil(input)) {
      return input;
    }
    input = input.toString();
    const matches = input.match(/IMP\d+-(.+)/);
    if (matches) {
      // matches would be ["IMPxxx-yyyy", "yyyy"]
      return matches[1];
    }

    return input;
  }
);
