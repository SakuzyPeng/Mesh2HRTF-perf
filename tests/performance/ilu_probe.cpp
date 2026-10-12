// Mesh2HRTF-perf regression probe, 2026-10-12. EUPL-1.2.

#include "NC_ConstantsVariables.h"
#include "NC_Arrays.h"
#include <iostream>
#include <fstream>
#include <iomanip>
extern Complex *zL_incom,*zU_incom;
extern int *nL_colnu,*nL_firnu,*nU_rownu,*nU_firnu;
void NC_IncompleteLUDecomposition(std::ofstream&);
void NC_IncompleteLUForBack(std::ofstream&,Vector<Complex>&,Vector<Complex>&);
void NC_DeleteIncompleteLUMatrices();
int main(){
    std::ofstream log("ilu_probe.log");int id,n,method,degree,nz;
    std::cout<<std::setprecision(17);
    while(std::cin>>id>>n>>method>>degree>>nz){
        numRowsOfCoefficientMatrix_=n;methodFMM_=method;scanningDegreeLU_=degree;numClusterLevels_=0;
        irownea=new int[n+1];jcolnea=new int[nz];zcoefl=new Complex[nz];zrhs=new Complex[n];
        irowsmtx=new int[n+1]();zsmtx=new Complex[0];
        for(int i=0;i<=n;++i)std::cin>>irownea[i];
        for(int i=0;i<nz;++i)std::cin>>jcolnea[i];
        for(int i=0;i<nz;++i){double a,b;std::cin>>a>>b;zcoefl[i].set(a,b);}
        for(int i=0;i<n;++i){double a,b;std::cin>>a>>b;zrhs[i].set(a,b);}
        NC_IncompleteLUDecomposition(log);
        std::cout<<"CASE "<<id<<" "<<n<<" "<<nL_firnu[n]<<" "<<nU_firnu[n]<<"\n";
        for(int i=0;i<=n;++i)std::cout<<nL_firnu[i]<<" "<<nU_firnu[i]<<"\n";
        for(int i=0;i<nL_firnu[n];++i)std::cout<<"L "<<nL_colnu[i]<<" "<<zL_incom[i].re()<<" "<<zL_incom[i].im()<<"\n";
        for(int i=0;i<nU_firnu[n];++i)std::cout<<"U "<<nU_rownu[i]<<" "<<zU_incom[i].re()<<" "<<zU_incom[i].im()<<"\n";
        Vector<Complex> rhs(n),answer(n);for(int i=0;i<n;++i)rhs[i]=zrhs[i];
        NC_IncompleteLUForBack(log,rhs,answer);
        for(int i=0;i<n;++i)std::cout<<"R "<<answer[i].re()<<" "<<answer[i].im()<<"\n";
        NC_DeleteIncompleteLUMatrices();delete[]irownea;delete[]jcolnea;delete[]zcoefl;delete[]zrhs;delete[]irowsmtx;delete[]zsmtx;
    }
}
