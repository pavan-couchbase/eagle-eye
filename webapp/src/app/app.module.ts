import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';

import { AppComponent } from './app.component';
import { AppbarComponent } from './appbar/appbar.component';
import { ApptabComponent } from './apptab/apptab.component';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { StoreModule } from '@ngrx/store';
import {MatToolbarModule} from "@angular/material/toolbar";
import {MatIconModule} from "@angular/material/icon";
import {MatTabsModule} from "@angular/material/tabs";
import { DashboardComponent } from './dashboard/dashboard.component';
import { JobManagerComponent } from './job-manager/job-manager.component';
import {MatFormFieldModule} from "@angular/material/form-field";
import {MatInputModule} from "@angular/material/input";
import {MatButtonModule} from "@angular/material/button";
import {MatDividerModule} from "@angular/material/divider";
import {MatExpansionModule} from "@angular/material/expansion";
import {EEService} from "./shared/services/async-ee.service";
import { EffectsModule } from '@ngrx/effects';
import {EagleEyeEffects} from "./shared/effects/ee.effects";
import {reducers} from "./shared/reducers";
import {HttpClientModule} from "@angular/common/http";
import {FormsModule} from "@angular/forms";
import {MatProgressBarModule} from "@angular/material/progress-bar";
import { DataViewerComponent } from './data-viewer/data-viewer.component';
import {MatPaginatorModule} from "@angular/material/paginator";
import {NgxChartsModule} from "@swimlane/ngx-charts";
import { ServerStatusComponent } from './server-status/server-status.component';
import {MatCheckboxModule} from "@angular/material/checkbox";
import {RouterModule} from "@angular/router";

@NgModule({
  declarations: [
    AppComponent,
    AppbarComponent,
    ApptabComponent,
    DashboardComponent,
    JobManagerComponent,
    DataViewerComponent,
    ServerStatusComponent,
  ],
  imports: [
    BrowserModule,
    BrowserAnimationsModule,
    HttpClientModule,
    StoreModule.forRoot(reducers),
    MatToolbarModule,
    MatIconModule,
    MatTabsModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatDividerModule,
    MatExpansionModule,
    EffectsModule.forRoot([EagleEyeEffects]),
    FormsModule,
    MatProgressBarModule,
    MatPaginatorModule,
    NgxChartsModule,
    MatCheckboxModule,
    RouterModule.forRoot([
      {path: '', component: DashboardComponent}
    ])
  ],
  providers: [EEService],
  bootstrap: [AppComponent]
})
export class AppModule { }
