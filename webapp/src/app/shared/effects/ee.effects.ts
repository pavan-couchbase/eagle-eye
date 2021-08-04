import { Injectable } from '@angular/core';
import { createEffect, Actions, ofType } from '@ngrx/effects';
import { Observable ,  of } from 'rxjs';
import { map, switchMap, catchError } from 'rxjs/operators';
import * as eeActions from '../actions/ee.actions';
import { EEService } from "../services/async-ee.service";

@Injectable()
export class EagleEyeEffects {
  constructor(private actions: Actions,
              private eeService: EEService) {}

  startEE$ = createEffect(() => {
    return this.actions.pipe(
      ofType(eeActions.START),
      switchMap(action => {
        return this.eeService.start((action as any).request.host,
          (action as any).request.clustername,
          (action as any).request.configfile,
          (action as any).request.restusername, (action as any).request.restpassword,
          (action as any).request.sshusername, (action as any).request.sshpassword,
          (action as any).request.dockerhost,
          (action as any).request.emails, (action as any).request.alertfrequency,
          (action as any).request.runOne).pipe(
            map(startResult => eeActions.StartSuccess({jobId: startResult.id})),
            catchError(startError => of(eeActions.StartFail({error: startError.Msg})))
          )
      })
    )
  });

  stopEE$ = createEffect(() => {
    return this.actions.pipe(
      ofType(eeActions.STOP),
      switchMap(action => {
        return this.eeService.stop((action as any).jobId).pipe(
          map(stopResult => eeActions.StopSuccess({msg: stopResult.Msg})),
          catchError(stopError => of(eeActions.StopFail({msg: stopError.Msg})))
        )
      })
    )
  })

  statusEE$ = createEffect(() => {
    return this.actions.pipe(
      ofType(eeActions.STATUS),
      switchMap(action => {
        return this.eeService.status((action as any).jobId).pipe(
          map(statusResult => eeActions.StatusSuccess({data: statusResult})),
          catchError(statusError => of(eeActions.StatusFail({error: statusError.Msg})))
        )
      })
    )
  })

  getDataEE$ = createEffect(() => {
    return this.actions.pipe(
      ofType(eeActions.GETDATA),
      switchMap(action => {
        return this.eeService.getData((action as any).request.jobId, (action as any).request.iter_num, (action as any).request.dc_name,
          (action as any).request.build, (action as any).request.cluster_name).pipe(
            map(getDataResult => eeActions.GetDataSuccess({data: getDataResult.data})),
            catchError(getDataError => of(eeActions.GetDataFail({Msg: getDataError.Msg})))
        )
      })
    )
  })

  serverStatusEE$ = createEffect(() => {
    return this.actions.pipe(
      ofType(eeActions.SERVERSTATUS),
      switchMap(action => {
        return this.eeService.serverStatus().pipe(
          map(serverStatusResult => eeActions.ServerStatusSuccess({data: serverStatusResult.data})),
          catchError(serverStatusError => of(eeActions.ServerStatusFail({Msg: serverStatusError.Msg})))
        )
      })
    )
  })

  uploadSupportalEE$ = createEffect(() => {
      return this.actions.pipe(
        ofType(eeActions.UPLOADSUPPORTAL),
        switchMap(action => {
          return this.eeService.uploadSupportal((action as any).request.jobId, (action as any).request.iter_num).pipe(
            map(uploadSupportalSuccess => eeActions.UploadSupportalSuccess({Msg: uploadSupportalSuccess.Msg})),
            catchError(uploadSupportalError => of(eeActions.UploadSupportalFail({Msg: uploadSupportalError.Msg})))
          )
        })
      )
  })
}
