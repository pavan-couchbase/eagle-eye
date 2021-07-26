import * as fromStart from './start.reducers';
import * as fromStop from './stop.reducers';
import * as fromStatus from './status.reducers';
import * as fromGetData from './get-data.reducers';

export const reducers = {
  start: fromStart.reducer,
  stop: fromStop.reducer,
  status: fromStatus.reducer,
  getData: fromGetData.reducer
}
