import * as eeActions from '../actions/ee.actions';
import {Action,createReducer, on} from "@ngrx/store";

export interface State {
  data: any;
  error: string;
}

export const initialState: State = {
  data: [],
  error: ""
}

export const serverStatusReducer = createReducer(
  initialState,
  on(eeActions.ServerStatus, (state) => ({
    ...state
  })),
  on(eeActions.ServerStatusSuccess, (state, {data}) => ({
    ...state,
    data: data
  })),
  on(eeActions.ServerStatusFail, (state, {Msg}) => ({
    ...state,
    error: Msg
  }))
)

export function reducer(state: State | undefined, action: Action) {
  return serverStatusReducer(state, action)
}
