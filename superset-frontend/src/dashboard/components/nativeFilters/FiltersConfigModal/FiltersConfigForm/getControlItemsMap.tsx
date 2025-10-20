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
import { CustomControlItem } from '@superset-ui/chart-controls';
import { ReactNode } from 'react';
import {
  Checkbox,
  FormItem,
  InfoTooltip,
  Tooltip,
  type FormInstance,
} from '@superset-ui/core/components';
import { t } from '@apache-superset/core/translation';
import {
  Filter,
  ChartCustomization,
  getChartControlPanelRegistry,
} from '@superset-ui/core';
import { styled } from '@apache-superset/core/theme';
import {
  doesColumnMatchFilterType,
  getControlItems,
  setNativeFilterFieldValues,
} from './utils';
import { NativeFiltersForm, NativeFiltersFormItem } from '../types';
import {
  StyledFormItem,
  StyledLabel,
  StyledRowFormItem,
} from './FiltersConfigForm';
import { ColumnSelect } from './ColumnSelect';

export interface ControlItemsProps {
  expanded: boolean;
  datasetId: number;
  disabled: boolean;
  forceUpdate: Function;
  formChanged: Function;
  form: FormInstance<NativeFiltersForm>;
  filterId: string;
  filterType: string;
  filterToEdit?: Filter;
  customizationToEdit?: ChartCustomization;
  formFilter?: NativeFiltersFormItem;
  removed?: boolean;
}

const CleanFormItem = styled(FormItem)`
  margin-bottom: 0;
`;

export default function getControlItemsMap({
  expanded,
  datasetId,
  disabled,
  forceUpdate,
  formChanged,
  form,
  filterId,
  filterType,
  filterToEdit,
  customizationToEdit,
  formFilter,
  removed,
}: ControlItemsProps) {
  const controlPanelRegistry = getChartControlPanelRegistry();
  const controlItems =
    getControlItems(controlPanelRegistry.get(filterType)) ?? [];
  const mapControlItems: Record<
    string,
    { element: ReactNode; checked: boolean }
  > = {};
  const mapMainControlItems: Record<
    string,
    { element: ReactNode; elementColumnValue?: ReactNode; checked: boolean }
  > = {};

  controlItems
    .filter(
      (mainControlItem: CustomControlItem) =>
        mainControlItem?.name === 'groupby',
    )
    .forEach(mainControlItem => {
      const initialValue =
        filterToEdit?.controlValues?.[mainControlItem.name] ??
        customizationToEdit?.controlValues?.[mainControlItem.name] ??
        mainControlItem?.config?.default;
      const initColumn =
        customizationToEdit?.targets?.[0]?.column?.name ??
        filterToEdit?.targets?.[0]?.column?.name;

      // set column value or nothing for keep default behavior column value = column name
      const initColumnValue = filterToEdit?.targets[0]?.column?.columnValue;

      const element = (
        <>
          <CleanFormItem
            name={['filters', filterId, 'requiredFirst', mainControlItem.name]}
            hidden
            initialValue={
              mainControlItem?.config?.requiredFirst &&
              filterToEdit?.requiredFirst
            }
          />
          <StyledFormItem
            expanded={expanded}
            // don't show the column select unless we have a dataset
            name={['filters', filterId, 'column']}
            initialValue={initColumn}
            label={
              <StyledLabel>
                {mainControlItem.config?.label || t('Column for labels')}
              </StyledLabel>
            }
            rules={[
              {
                required: mainControlItem.config?.required && !removed, // TODO: need to move ColumnSelect settings to controlPanel for all filters
                message: t('Column is required'),
              },
            ]}
            extra={t(
              "Column used for labels and values or only labels if a value is defined on 'Column for values'",
            )}
            data-test="field-input"
          >
            <ColumnSelect
              mode={mainControlItem.config?.multiple && 'multiple'}
              form={form}
              filterId={filterId}
              datasetId={datasetId}
              filterValues={column =>
                doesColumnMatchFilterType(
                  formFilter?.filterType || '',
                  column,
                ) && !!column?.filterable
              }
              onChange={() => {
                // when value change, we reset column value
                form.setFieldsValue({
                  filters: { [filterId]: { columnValue: undefined } },
                });
                // We need reset default value when column changed
                setNativeFilterFieldValues(form, filterId, {
                  defaultDataMask: null,
                });
                forceUpdate();
                formChanged();
              }}
            />
          </StyledFormItem>
        </>
      );

      const elementColumnValue = (
        <>
          <StyledFormItem
            expanded={expanded}
            name={['filters', filterId, 'columnValue']}
            initialValue={initColumnValue}
            label={
              <StyledLabel>
                {t('Column for values')}
                &nbsp;
                <InfoTooltip
                  placement="top"
                  tooltip={t(
                    'If value is specified, filtering will be done based on this value. Default value will be column name.',
                  )}
                />
              </StyledLabel>
            }
          >
            <ColumnSelect
              mode={mainControlItem.config?.multiple && 'multiple'}
              form={form}
              formField="columnValue"
              filterId={filterId}
              datasetId={datasetId}
              allowClear
              filterValues={column =>
                doesColumnMatchFilterType(formFilter?.filterType || '', column)
              }
              onChange={() => {
                // We need reset default value when column value changed
                setNativeFilterFieldValues(form, filterId, {
                  defaultDataMask: null,
                });
                forceUpdate();
                formChanged();
              }}
            />
          </StyledFormItem>
        </>
      );
      mapMainControlItems[mainControlItem.name] = {
        element,
        elementColumnValue,
        checked: initialValue,
      };
    });
  controlItems
    .filter(
      (controlItem: CustomControlItem) =>
        controlItem?.config?.renderTrigger &&
        controlItem.name !== 'sortAscending' &&
        controlItem.name !== 'enableSingleValue',
    )
    .forEach(controlItem => {
      const initialValue =
        filterToEdit?.controlValues?.[controlItem.name] ??
        customizationToEdit?.controlValues?.[controlItem.name] ??
        controlItem?.config?.default;
      const element = (
        <>
          <CleanFormItem
            name={['filters', filterId, 'requiredFirst', controlItem.name]}
            hidden
            initialValue={
              controlItem?.config?.requiredFirst && filterToEdit?.requiredFirst
            }
          />
          <Tooltip
            key={controlItem.name}
            placement="left"
            title={
              controlItem.config.affectsDataMask &&
              disabled &&
              t('Populate "Default value" to enable this control')
            }
          >
            <StyledRowFormItem
              expanded={expanded}
              key={controlItem.name}
              name={['filters', filterId, 'controlValues', controlItem.name]}
              initialValue={initialValue}
              valuePropName="checked"
              colon={false}
            >
              <Checkbox
                disabled={controlItem.config.affectsDataMask && disabled}
                onChange={checked => {
                  if (controlItem.config.requiredFirst) {
                    setNativeFilterFieldValues(form, filterId, {
                      requiredFirst: {
                        ...formFilter?.requiredFirst,
                        [controlItem.name]: checked,
                      },
                    });
                  }
                  if (controlItem.config.resetConfig) {
                    setNativeFilterFieldValues(form, filterId, {
                      defaultDataMask: null,
                    });
                  }
                  formChanged();
                  forceUpdate();
                }}
              >
                <>
                  {controlItem.config.label}&nbsp;
                  {controlItem.config.description && (
                    <InfoTooltip
                      placement="top"
                      tooltip={controlItem.config.description}
                    />
                  )}
                </>
              </Checkbox>
            </StyledRowFormItem>
          </Tooltip>
        </>
      );
      mapControlItems[controlItem.name] = { element, checked: initialValue };
    });
  return {
    controlItems: mapControlItems,
    mainControlItems: mapMainControlItems,
  };
}
