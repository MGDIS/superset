/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */
import { JsonObject } from '@superset-ui/core';

jest.mock('src/utils/getBootstrapData');

// The constant is evaluated on import, so each case needs a fresh module registry.
const loadPageSize = (conf: JsonObject) => {
  jest.resetModules();
  // eslint-disable-next-line global-require, @typescript-eslint/no-var-requires
  const getBootstrapData = require('src/utils/getBootstrapData').default;
  getBootstrapData.mockReturnValue({ common: { conf } });
  // eslint-disable-next-line global-require, @typescript-eslint/no-var-requires
  return require('./constants').PAGE_SIZE;
};

test('falls back to 25 when the config key is absent', () => {
  expect(loadPageSize({})).toBe(25);
});

test('uses the LIST_VIEW_PAGE_SIZE config key when set', () => {
  expect(loadPageSize({ LIST_VIEW_PAGE_SIZE: 10 })).toBe(10);
});
